#!/usr/bin/env python3
"""
🔗 Coralogix MCP Client for Real DataPrime Query Execution

This module implements the MCP (Model Context Protocol) client to execute
generated DataPrime queries against real Coralogix observability data using
the available MCP function tools.
"""

import os
import asyncio
import json
import re
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Union, Tuple, Callable
from dataclasses import dataclass
from enum import Enum
import time


class QueryType(Enum):
    """Supported query types for Coralogix MCP execution."""
    LOGS = "logs"
    SPANS = "spans"
    METRICS_INSTANT = "metrics_instant" 
    METRICS_RANGE = "metrics_range"


@dataclass
class QueryResult:
    """Structured result from MCP query execution."""
    success: bool
    query_type: QueryType
    original_query: str
    results: List[Dict[str, Any]]
    metadata: Dict[str, Any]
    execution_time_ms: float
    result_count: int
    error_message: Optional[str] = None
    warnings: List[str] = None
    
    def __post_init__(self):
        if self.warnings is None:
            self.warnings = []


@dataclass 
class MCPConnectionStatus:
    """MCP connection health and capabilities."""
    connected: bool
    endpoint: str
    authenticated: bool
    capabilities: List[str]
    last_test_time: datetime
    error_message: Optional[str] = None


class CoralogixMCPClient:
    """
    Coralogix MCP Client for executing DataPrime queries against real data.
    
    This client uses the available MCP function tools to provide seamless
    integration with Coralogix observability data.
    """
    
    def __init__(self, mcp_functions: Optional[Dict[str, Callable]] = None):
        """
        Initialize the Coralogix MCP client.
        
        Args:
            mcp_functions: Dictionary of available MCP function calls
        """
        # Store reference to MCP function calls (will be injected from main app)
        self.mcp_functions = mcp_functions or {}
        
        self._connection_status: Optional[MCPConnectionStatus] = None
        
        # Query parsing patterns
        self._query_patterns = {
            'source_logs': re.compile(r'source\s+logs', re.IGNORECASE),
            'source_spans': re.compile(r'source\s+spans', re.IGNORECASE),
            'time_range': re.compile(r'last\s+(\d+[mhd])', re.IGNORECASE),
            'between_times': re.compile(r'between\s+(.+?)\s+and\s+(.+)', re.IGNORECASE)
        }
        
        # Setup logging
        self.logger = logging.getLogger(__name__)
    
    def _parse_dataprime_query(self, query: str) -> Tuple[QueryType, Dict[str, Any]]:
        """
        Parse a DataPrime query to determine type and extract parameters.
        
        Args:
            query: Raw DataPrime query string
            
        Returns:
            Tuple of (QueryType, query_params)
        """
        query = query.strip()
        params = {}
        
        # Determine query type based on source
        if self._query_patterns['source_logs'].search(query):
            query_type = QueryType.LOGS
        elif self._query_patterns['source_spans'].search(query):
            query_type = QueryType.SPANS
        else:
            # Default to logs if unclear
            query_type = QueryType.LOGS
        
        # Extract time range
        time_match = self._query_patterns['time_range'].search(query)
        if time_match:
            time_str = time_match.group(1).lower()
            params['time_range'] = self._convert_time_range(time_str)
        else:
            # Default to last 1 hour
            params['time_range'] = {
                'start': (datetime.now() - timedelta(hours=1)).isoformat() + 'Z',
                'end': datetime.now().isoformat() + 'Z'
            }
        
        # Store cleaned query
        params['cleaned_query'] = query
        
        return query_type, params
    
    def _convert_time_range(self, time_str: str) -> Dict[str, str]:
        """Convert DataPrime time range to ISO format."""
        now = datetime.now()
        
        if time_str.endswith('m'):
            minutes = int(time_str[:-1])
            start_time = now - timedelta(minutes=minutes)
        elif time_str.endswith('h'):
            hours = int(time_str[:-1])
            start_time = now - timedelta(hours=hours)
        elif time_str.endswith('d'):
            days = int(time_str[:-1])
            start_time = now - timedelta(days=days)
        else:
            # Default to 1 hour
            start_time = now - timedelta(hours=1)
        
        return {
            'start': start_time.isoformat() + 'Z',
            'end': now.isoformat() + 'Z'
        }
    
    async def test_connection(self) -> MCPConnectionStatus:
        """
        Test the MCP connection to Coralogix.
        
        Returns:
            Connection status with capabilities
        """
        try:
            start_time = time.time()
            
            # Test with a simple query to validate connection
            if 'get_logs' in self.mcp_functions:
                # Try a minimal logs query
                test_result = await self._execute_logs_query_via_mcp(
                    query="source logs last 5m | limit 1",
                    start_date=(datetime.now() - timedelta(minutes=5)).isoformat() + 'Z',
                    end_date=datetime.now().isoformat() + 'Z',
                    limit=1
                )
                
                capabilities = []
                if 'get_logs' in self.mcp_functions:
                    capabilities.append("logs")
                if 'get_traces' in self.mcp_functions:
                    capabilities.append("spans")
                if 'metrics_instant_query' in self.mcp_functions:
                    capabilities.append("metrics")
                if 'get_schemas' in self.mcp_functions:
                    capabilities.append("schemas")
                
                self._connection_status = MCPConnectionStatus(
                    connected=True,
                    endpoint="mcp://coralogix-server",
                    authenticated=True,
                    capabilities=capabilities,
                    last_test_time=datetime.now()
                )
            else:
                raise Exception("No MCP functions available")
            
            return self._connection_status
            
        except Exception as e:
            self._connection_status = MCPConnectionStatus(
                connected=False,
                endpoint="mcp://coralogix-server",
                authenticated=False,
                capabilities=[],
                last_test_time=datetime.now(),
                error_message=str(e)
            )
            
            return self._connection_status
    
    async def execute_dataprime_query(self, 
                                    query: str, 
                                    limit: int = 50,
                                    timeout_seconds: int = 30) -> QueryResult:
        """
        Execute a DataPrime query against Coralogix data.
        
        Args:
            query: DataPrime query string
            limit: Maximum number of results to return
            timeout_seconds: Query timeout in seconds
            
        Returns:
            QueryResult with execution results and metadata
        """
        start_time = time.time()
        
        try:
            # Parse the query to determine type and parameters
            query_type, params = self._parse_dataprime_query(query)
            
            # Execute based on query type
            if query_type == QueryType.LOGS:
                results = await self._execute_logs_query_via_mcp(
                    query=query,
                    start_date=params['time_range']['start'],
                    end_date=params['time_range']['end'],
                    limit=limit
                )
            elif query_type == QueryType.SPANS:
                results = await self._execute_spans_query_via_mcp(
                    query=query,
                    start_date=params['time_range']['start'],
                    end_date=params['time_range']['end'],
                    limit=limit
                )
            else:
                raise ValueError(f"Unsupported query type: {query_type}")
            
            execution_time_ms = (time.time() - start_time) * 1000
            
            return QueryResult(
                success=True,
                query_type=query_type,
                original_query=query,
                results=results,
                metadata={
                    'query_parsed': params,
                    'limit_applied': limit,
                    'timeout_seconds': timeout_seconds,
                    'mcp_functions_available': list(self.mcp_functions.keys())
                },
                execution_time_ms=execution_time_ms,
                result_count=len(results)
            )
            
        except Exception as e:
            execution_time_ms = (time.time() - start_time) * 1000
            
            return QueryResult(
                success=False,
                query_type=QueryType.LOGS,  # Default
                original_query=query,
                results=[],
                metadata={'error_occurred_at_ms': execution_time_ms},
                execution_time_ms=execution_time_ms,
                result_count=0,
                error_message=str(e)
            )
    
    async def _execute_logs_query_via_mcp(self, 
                                        query: str, 
                                        start_date: str, 
                                        end_date: str, 
                                        limit: int) -> List[Dict[str, Any]]:
        """Execute a logs query via available MCP function."""
        if 'get_logs' not in self.mcp_functions:
            raise Exception("MCP logs function not available")
        
        try:
            # Call the actual MCP function
            mcp_result = await self.mcp_functions['get_logs'](
                query=query,
                startDate=start_date,
                endDate=end_date,
                limit=limit
            )
            
            # Extract results based on expected MCP response format
            if isinstance(mcp_result, dict):
                if 'results' in mcp_result:
                    return mcp_result['results']
                elif 'data' in mcp_result:
                    return mcp_result['data']
                else:
                    return [mcp_result]  # Single result
            elif isinstance(mcp_result, list):
                return mcp_result
            else:
                return []
                
        except Exception as e:
            self.logger.error(f"MCP logs query failed: {e}")
            raise
    
    async def _execute_spans_query_via_mcp(self, 
                                         query: str, 
                                         start_date: str, 
                                         end_date: str, 
                                         limit: int) -> List[Dict[str, Any]]:
        """Execute a spans query via available MCP function."""
        if 'get_traces' not in self.mcp_functions:
            raise Exception("MCP traces function not available")
        
        try:
            # Call the actual MCP function
            mcp_result = await self.mcp_functions['get_traces'](
                query=query,
                startDate=start_date,
                endDate=end_date,
                limit=limit
            )
            
            # Extract results based on expected MCP response format
            if isinstance(mcp_result, dict):
                if 'results' in mcp_result:
                    return mcp_result['results']
                elif 'data' in mcp_result:
                    return mcp_result['data']
                else:
                    return [mcp_result]  # Single result
            elif isinstance(mcp_result, list):
                return mcp_result
            else:
                return []
                
        except Exception as e:
            self.logger.error(f"MCP spans query failed: {e}")
            raise
    
    async def get_data_schema(self, 
                            dataset_type: str = "logs", 
                            time_range_hours: int = 24) -> Dict[str, Any]:
        """
        Get data schema for better query construction.
        
        Args:
            dataset_type: Type of dataset ("logs", "spans", "metrics")
            time_range_hours: Hours to look back for schema discovery
            
        Returns:
            Schema information with available fields
        """
        if 'get_schemas' not in self.mcp_functions:
            return {
                "error": "Schema function not available",
                "schema_available": False
            }
        
        try:
            end_time = datetime.now()
            start_time = end_time - timedelta(hours=time_range_hours)
            
            schema_result = await self.mcp_functions['get_schemas'](
                datasetType=f"DATASET_TYPE_{dataset_type.upper()}",
                startDate=start_time.isoformat() + 'Z',
                endDate=end_time.isoformat() + 'Z',
                limit=100,
                includedExamples=2
            )
            
            return schema_result if isinstance(schema_result, dict) else {"data": schema_result}
            
        except Exception as e:
            return {
                "error": str(e),
                "schema_available": False
            }
    
    def get_connection_status(self) -> Optional[MCPConnectionStatus]:
        """Get the current connection status."""
        return self._connection_status
    
    async def execute_query_with_analysis_context(self, 
                                                query: str, 
                                                original_user_input: str) -> Dict[str, Any]:
        """
        Execute query and return results with context for AI analysis.
        
        This method is specifically designed for the voice assistant's
        AI analysis pipeline.
        
        Args:
            query: Generated DataPrime query
            original_user_input: Original user voice input
            
        Returns:
            Complete context for AI analysis including results and metadata
        """
        # Execute the main query
        result = await self.execute_dataprime_query(query, limit=50)
        
        # Add analysis context
        analysis_context = {
            'query_execution': result,
            'user_intent': {
                'original_input': original_user_input,
                'generated_query': query,
                'inferred_goal': self._infer_user_goal(original_user_input)
            },
            'analysis_hints': {
                'focus_areas': self._suggest_focus_areas(result),
                'potential_issues': self._identify_potential_issues(result),
                'follow_up_questions': self._suggest_follow_ups(result, original_user_input)
            }
        }
        
        return analysis_context
    
    def _infer_user_goal(self, user_input: str) -> str:
        """Infer what the user is trying to accomplish."""
        user_input_lower = user_input.lower()
        
        if any(word in user_input_lower for word in ['error', 'fail', 'exception']):
            return 'troubleshooting_errors'
        elif any(word in user_input_lower for word in ['slow', 'performance', 'latency']):
            return 'performance_analysis'
        elif any(word in user_input_lower for word in ['count', 'how many', 'total']):
            return 'metric_analysis'
        elif any(word in user_input_lower for word in ['service', 'application', 'system']):
            return 'service_health_check'
        else:
            return 'general_investigation'
    
    def _suggest_focus_areas(self, result: QueryResult) -> List[str]:
        """Suggest what to focus on in the results."""
        focus_areas = []
        
        if result.success and result.results:
            # Check for common patterns in results
            sample = result.results[:5]  # Look at first 5 results
            
            # Look for error patterns
            if any('error' in str(item).lower() for item in sample):
                focus_areas.append('error_patterns')
            
            # Look for performance indicators
            if any('duration' in str(item) or 'response_time' in str(item) for item in sample):
                focus_areas.append('performance_metrics')
            
            # Look for service indicators
            if any('service' in str(item) or 'subsystem' in str(item) for item in sample):
                focus_areas.append('service_breakdown')
                
        return focus_areas
    
    def _identify_potential_issues(self, result: QueryResult) -> List[str]:
        """Identify potential issues in the results."""
        issues = []
        
        if not result.success:
            issues.append(f"query_execution_failed: {result.error_message}")
        elif result.result_count == 0:
            issues.append("no_data_found")
        elif result.execution_time_ms > 5000:
            issues.append("slow_query_execution")
        elif result.result_count >= 50:
            issues.append("results_may_be_truncated")
            
        return issues
    
    def _suggest_follow_ups(self, result: QueryResult, original_input: str) -> List[str]:
        """Suggest follow-up questions based on results."""
        follow_ups = []
        
        if result.success and result.results:
            if 'error' in original_input.lower():
                follow_ups.extend([
                    "When did these errors start?",
                    "Which services are most affected?", 
                    "What's the error rate trend?"
                ])
            elif 'slow' in original_input.lower() or 'performance' in original_input.lower():
                follow_ups.extend([
                    "What's causing the slowest requests?",
                    "How does this compare to yesterday?",
                    "Which endpoints need attention?"
                ])
        
        return follow_ups


# Factory function for creating MCP client with proper function injection
def create_mcp_client_with_functions(mcp_function_map: Dict[str, Callable]) -> CoralogixMCPClient:
    """
    Create an MCP client with injected function references.
    
    Args:
        mcp_function_map: Dictionary mapping function names to actual MCP function calls
        
    Returns:
        Configured CoralogixMCPClient instance
    """
    return CoralogixMCPClient(mcp_functions=mcp_function_map)


# Convenience functions for integration with voice assistant
async def execute_query_for_voice_assistant(query: str, 
                                          original_input: str,
                                          mcp_functions: Dict[str, Callable]) -> Dict[str, Any]:
    """
    Execute a DataPrime query for the voice assistant with full context.
    
    This is the main entry point for the voice assistant integration.
    """
    client = create_mcp_client_with_functions(mcp_functions)
    return await client.execute_query_with_analysis_context(query, original_input)


# Module initialization
__all__ = [
    'CoralogixMCPClient',
    'QueryResult', 
    'MCPConnectionStatus',
    'QueryType',
    'create_mcp_client_with_functions',
    'execute_query_for_voice_assistant'
] 