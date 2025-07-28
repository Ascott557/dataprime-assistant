#!/usr/bin/env python3
"""
🧠 AI-Powered Result Analyzer for DataPrime Query Results

This module provides intelligent analysis of real Coralogix query results,
generating conversational insights suitable for voice interaction.
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass
from coralogix_mcp_client import QueryResult, QueryType


@dataclass
class AnalysisResult:
    """Structured analysis result for voice response generation."""
    summary: str
    key_insights: List[str]
    patterns_detected: List[Dict[str, Any]]
    recommendations: List[str]
    follow_up_suggestions: List[str]
    urgency_level: str  # "low", "medium", "high", "critical"
    data_quality: Dict[str, Any]
    conversational_response: str


class DataPrimeResultAnalyzer:
    """
    AI-powered analyzer for DataPrime query results.
    
    This analyzer takes real query results and generates intelligent,
    conversational insights suitable for voice interaction.
    """
    
    def __init__(self, openai_client):
        """
        Initialize the result analyzer.
        
        Args:
            openai_client: OpenAI client for GPT-4 analysis
        """
        self.openai_client = openai_client
        self.logger = logging.getLogger(__name__)
    
    async def analyze_query_results(self, 
                                  query_result: QueryResult, 
                                  original_user_input: str,
                                  analysis_context: Dict[str, Any] = None) -> AnalysisResult:
        """
        Analyze query results and generate conversational insights.
        
        Args:
            query_result: Results from MCP query execution
            original_user_input: Original user voice input
            analysis_context: Additional context for analysis
            
        Returns:
            AnalysisResult with conversational insights
        """
        try:
            # Generate comprehensive analysis using GPT-4
            analysis_prompt = self._build_analysis_prompt(
                query_result, original_user_input, analysis_context
            )
            
            response = await self.openai_client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": self._get_system_prompt()},
                    {"role": "user", "content": analysis_prompt}
                ],
                max_tokens=600,
                temperature=0.3,  # Lower temperature for more consistent JSON
                timeout=15.0  # 15 second timeout
            )
            
            analysis_text = response.choices[0].message.content.strip()
            
            # Parse the structured response
            return self._parse_analysis_response(analysis_text, query_result, original_user_input)
            
        except Exception as e:
            self.logger.error(f"Analysis failed: {e}")
            return self._create_fallback_analysis(query_result, original_user_input)
    
    def _get_system_prompt(self) -> str:
        """Get the system prompt for AI analysis."""
        return """You are an expert observability engineer analyzing real query results from a Coralogix DataPrime query.

Your task is to provide intelligent, conversational analysis that is suitable for text-to-speech delivery.

CRITICAL: You MUST respond with valid JSON only. No other text before or after the JSON.

Required JSON structure:
{
  "summary": "Brief overview in 1-2 sentences",
  "key_insights": ["insight1", "insight2", "insight3"],
  "recommendations": ["action1", "action2", "action3"],
  "urgency_level": "low|medium|high|critical",
  "conversational_response": "Natural, conversational explanation in 2-3 sentences that sounds like you're talking to a colleague"
}

Guidelines:
- Make the conversational_response sound natural and human-like
- Focus on what matters most to an engineer troubleshooting their system
- Use plain English, avoid technical jargon in the conversational response
- Be specific about numbers, timeframes, and services when relevant
- If no issues found, acknowledge the healthy state
- Keep insights and recommendations concise and actionable"""
    
    def _build_analysis_prompt(self, 
                              query_result: QueryResult, 
                              original_user_input: str,
                              analysis_context: Dict[str, Any] = None) -> str:
        """Build the analysis prompt with query results and context."""
        
        # Prepare result summary
        if query_result.success:
            result_summary = f"""
Query executed successfully in {query_result.execution_time_ms:.0f}ms
Results: {query_result.result_count} records
Query Type: {query_result.query_type.value}
"""
            
            # Include sample results (first 3-5 for analysis)
            sample_results = query_result.results[:5] if query_result.results else []
            results_preview = json.dumps(sample_results, indent=2, default=str)[:1000]
        else:
            result_summary = f"""
Query failed: {query_result.error_message}
Execution time: {query_result.execution_time_ms:.0f}ms
Query Type: {query_result.query_type.value}
"""
            results_preview = "No results available due to query failure"
        
        # Build comprehensive prompt
        prompt = f"""
OBSERVABILITY ANALYSIS REQUEST

Original User Question: "{original_user_input}"
Generated DataPrime Query: {query_result.original_query}

EXECUTION RESULTS:
{result_summary}

SAMPLE DATA:
{results_preview}

ANALYSIS CONTEXT:
- User Intent: {analysis_context.get('user_intent', {}).get('inferred_goal', 'general_investigation') if analysis_context else 'general_investigation'}
- Detected Patterns: {analysis_context.get('analysis_hints', {}).get('focus_areas', []) if analysis_context else []}
- Potential Issues: {analysis_context.get('analysis_hints', {}).get('potential_issues', []) if analysis_context else []}

Analyze this observability data and provide insights that would be valuable to a DevOps engineer or SRE.
Focus on system health, performance patterns, and actionable recommendations.
Make your conversational response sound natural and helpful, as if you're explaining findings to a colleague."""
        
        return prompt
    
    def _parse_analysis_response(self, 
                               analysis_text: str, 
                               query_result: QueryResult,
                               original_user_input: str) -> AnalysisResult:
        """Parse the structured AI analysis response with robust JSON extraction."""
        try:
            # Clean and extract JSON from the response
            json_text = self._extract_json_from_text(analysis_text)
            
            if json_text:
                analysis_data = json.loads(json_text)
                
                # Validate required fields
                if not isinstance(analysis_data, dict):
                    raise ValueError("Analysis response is not a valid JSON object")
                
                return AnalysisResult(
                    summary=analysis_data.get('summary', 'Analysis completed successfully'),
                    key_insights=self._ensure_list(analysis_data.get('key_insights', [])),
                    patterns_detected=analysis_data.get('patterns_detected', []),
                    recommendations=self._ensure_list(analysis_data.get('recommendations', [])),
                    follow_up_suggestions=self._generate_default_followups(original_user_input),
                    urgency_level=analysis_data.get('urgency_level', 'low'),
                    data_quality=self._assess_data_quality(query_result),
                    conversational_response=analysis_data.get('conversational_response', 
                                                            self._generate_fallback_response(query_result, original_user_input))
                )
            else:
                # Fallback to text parsing
                return self._parse_text_analysis(analysis_text, query_result, original_user_input)
                
        except (json.JSONDecodeError, ValueError) as e:
            self.logger.warning(f"JSON parsing failed: {e}, falling back to text parsing")
            return self._parse_text_analysis(analysis_text, query_result, original_user_input)
    
    def _parse_text_analysis(self, 
                           analysis_text: str, 
                           query_result: QueryResult,
                           original_user_input: str) -> AnalysisResult:
        """Parse unstructured analysis text as fallback."""
        
        # Extract key information from text
        lines = analysis_text.split('\n')
        insights = []
        recommendations = []
        
        for line in lines:
            line = line.strip()
            if line and not line.startswith('#'):
                if any(word in line.lower() for word in ['insight', 'finding', 'noticed']):
                    insights.append(line)
                elif any(word in line.lower() for word in ['recommend', 'suggest', 'should']):
                    recommendations.append(line)
        
        # Determine urgency based on content
        urgency = 'low'
        if any(word in analysis_text.lower() for word in ['critical', 'urgent', 'error', 'down']):
            urgency = 'critical'
        elif any(word in analysis_text.lower() for word in ['warning', 'slow', 'issue']):
            urgency = 'medium'
        
        # Create natural conversational response
        if query_result.success and query_result.result_count > 0:
            conversational_response = f"I found {query_result.result_count} results for your query about {original_user_input.lower()}. "
            
            # Try to extract meaningful insights from the text
            if any(word in analysis_text.lower() for word in ['error', 'critical', 'warning']):
                conversational_response += "I noticed some issues that need attention."
            elif any(word in analysis_text.lower() for word in ['normal', 'healthy', 'successful']):
                conversational_response += "Everything looks healthy and operating normally."
            else:
                conversational_response += "The data shows typical operational patterns."
        elif query_result.success:
            conversational_response = f"Your query about {original_user_input.lower()} didn't return any results. This might mean the condition you're looking for isn't present in the current time range."
        else:
            conversational_response = f"I encountered an issue executing your query about {original_user_input.lower()}. The error was: {query_result.error_message}"
        
        return AnalysisResult(
            summary=analysis_text[:200] + "..." if len(analysis_text) > 200 else analysis_text,
            key_insights=insights[:3],  # Top 3 insights
            patterns_detected=[],
            recommendations=recommendations[:3],  # Top 3 recommendations
            follow_up_suggestions=self._generate_default_followups(original_user_input),
            urgency_level=urgency,
            data_quality=self._assess_data_quality(query_result),
            conversational_response=conversational_response
        )
    
    def _extract_json_from_text(self, text: str) -> Optional[str]:
        """Extract JSON from text that might contain markdown formatting or other content."""
        text = text.strip()
        
        # Remove markdown code blocks if present
        if text.startswith('```json'):
            text = text[7:]  # Remove ```json
        if text.startswith('```'):
            text = text[3:]  # Remove ```
        if text.endswith('```'):
            text = text[:-3]  # Remove closing ```
        
        text = text.strip()
        
        # Try to find JSON object boundaries
        start_idx = text.find('{')
        if start_idx == -1:
            return None
        
        # Find the matching closing brace
        brace_count = 0
        end_idx = -1
        
        for i, char in enumerate(text[start_idx:], start_idx):
            if char == '{':
                brace_count += 1
            elif char == '}':
                brace_count -= 1
                if brace_count == 0:
                    end_idx = i + 1
                    break
        
        if end_idx == -1:
            # If we can't find matching braces, try the whole text after the first {
            return text[start_idx:]
        
        return text[start_idx:end_idx]
    
    def _ensure_list(self, value: Any) -> List[str]:
        """Ensure the value is a list of strings."""
        if isinstance(value, list):
            return [str(item) for item in value if item]  # Convert to strings and filter empty
        elif isinstance(value, str):
            return [value] if value else []
        else:
            return []
    
    def _generate_fallback_response(self, query_result: QueryResult, original_user_input: str) -> str:
        """Generate a natural fallback response when AI analysis fails."""
        if query_result.success:
            if query_result.result_count > 0:
                return f"I found {query_result.result_count} results for your query about {original_user_input.lower()}. The data looks healthy with no immediate issues detected."
            else:
                return f"Your query about {original_user_input.lower()} didn't return any results. This could mean the condition you're looking for isn't present in the selected time range, which might actually be good news."
        else:
            return f"I encountered an issue executing your query about {original_user_input.lower()}. Let me know if you'd like to try a different approach or time range."

    def _assess_data_quality(self, query_result: QueryResult) -> Dict[str, Any]:
        """Assess the quality and completeness of query results."""
        quality_assessment = {
            'execution_success': query_result.success,
            'result_count': query_result.result_count,
            'execution_time_ms': query_result.execution_time_ms,
            'data_completeness': 'good' if query_result.result_count > 0 else 'no_data',
            'performance': 'good' if query_result.execution_time_ms < 2000 else 'slow'
        }
        
        if query_result.success:
            if query_result.result_count == 0:
                quality_assessment['issues'] = ['no_results_found']
            elif query_result.result_count >= 50:
                quality_assessment['issues'] = ['results_may_be_truncated'] 
            else:
                quality_assessment['issues'] = []
        else:
            quality_assessment['issues'] = ['query_execution_failed']
        
        return quality_assessment
    
    def _generate_default_followups(self, original_user_input: str) -> List[str]:
        """Generate default follow-up suggestions based on user input."""
        user_input_lower = original_user_input.lower()
        
        if 'error' in user_input_lower:
            return [
                "When did these errors start?",
                "Which services are most affected?",
                "What's the error rate over time?"
            ]
        elif any(word in user_input_lower for word in ['slow', 'performance', 'latency']):
            return [
                "What's causing the slowest requests?",
                "How does this compare to previous periods?",
                "Which endpoints need attention?"
            ]
        elif 'service' in user_input_lower:
            return [
                "How is service health trending?",
                "Are there any deployment correlations?",
                "What's the error rate for this service?"
            ]
        else:
            return [
                "Would you like to see a different time range?",
                "Should we look at related metrics?",
                "Any specific patterns to investigate?"
            ]
    
    def _create_fallback_analysis(self, 
                                query_result: QueryResult, 
                                original_user_input: str) -> AnalysisResult:
        """Create a fallback analysis when AI analysis fails."""
        
        if query_result.success:
            if query_result.result_count > 0:
                summary = f"Found {query_result.result_count} results in {query_result.execution_time_ms:.0f}ms"
                
                # Analyze the sample data to give better insights
                sample_data = str(query_result.results[:3]).lower() if query_result.results else ""
                
                if 'error' in sample_data or 'failed' in sample_data:
                    conversational_response = f"I found {query_result.result_count} results for your query about {original_user_input.lower()}. I detected some error patterns that you should investigate."
                    urgency = 'medium'
                elif 'success' in sample_data or '200' in sample_data:
                    conversational_response = f"I found {query_result.result_count} results for your query about {original_user_input.lower()}. The data shows healthy operations with successful responses."
                    urgency = 'low'
                else:
                    conversational_response = f"I found {query_result.result_count} results for your query about {original_user_input.lower()}. The query executed successfully and returned relevant data."
                    urgency = 'low'
            else:
                summary = "Query executed successfully but returned no results"
                conversational_response = f"Your query about {original_user_input.lower()} didn't return any results. This might mean the condition you're looking for isn't present in the current time range, which could actually be good news depending on what you're looking for."
                urgency = 'low'
        else:
            summary = f"Query failed: {query_result.error_message}"
            conversational_response = f"I encountered an issue executing your query about {original_user_input.lower()}. The error was: {query_result.error_message}. Let me know if you'd like to try a different approach."
            urgency = 'high'
        
        return AnalysisResult(
            summary=summary,
            key_insights=['Basic query execution completed'],
            patterns_detected=[],
            recommendations=['Try adjusting the time range or query parameters'],
            follow_up_suggestions=self._generate_default_followups(original_user_input),
            urgency_level=urgency,
            data_quality=self._assess_data_quality(query_result),
            conversational_response=conversational_response
        )


# Convenience function for voice assistant integration
async def analyze_results_for_voice_assistant(query_result: QueryResult,
                                            original_user_input: str,
                                            openai_client,
                                            analysis_context: Dict[str, Any] = None) -> AnalysisResult:
    """
    Analyze query results for voice assistant with intelligent insights.
    
    This is the main entry point for the voice assistant integration.
    """
    analyzer = DataPrimeResultAnalyzer(openai_client)
    return await analyzer.analyze_query_results(query_result, original_user_input, analysis_context)


# Module exports
__all__ = [
    'DataPrimeResultAnalyzer',
    'AnalysisResult',
    'analyze_results_for_voice_assistant'
] 