#!/usr/bin/env python3
"""
💬 Conversation Context Manager for Voice-Driven DataPrime Assistant

Maintains conversation state, handles follow-up queries, and provides context
for enhanced natural language understanding across multiple voice interactions.
"""

import time
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from opentelemetry import trace
import logging

logger = logging.getLogger(__name__)

@dataclass
class ConversationTurn:
    """Represents a single turn in the conversation."""
    turn_id: str
    timestamp: str
    user_input: str
    transcript_confidence: float
    intent: str
    generated_query: str
    validation_result: Dict[str, Any]
    response_text: str
    query_results: Optional[Dict[str, Any]] = None
    voice_processing_time: float = 0.0

@dataclass
class InvestigationContext:
    """Tracks ongoing investigation state."""
    focus_area: str  # e.g., "performance", "errors", "frontend_service"
    active_services: List[str]
    time_range: str  # e.g., "last 1h", "last 24h"
    key_findings: List[str]
    hypothesis: Optional[str] = None

@dataclass
class ConversationMetadata:
    """Metadata about the conversation session."""
    session_id: str
    user_id: Optional[str]
    start_time: str
    last_activity: str
    total_turns: int
    successful_queries: int
    failed_queries: int
    primary_intent: str
    voice_enabled: bool = True


class ConversationContext:
    """
    Manages conversation state and context for voice-driven interactions.
    
    Provides:
    - Turn-by-turn conversation history
    - Context for follow-up queries ("what about yesterday?")
    - Investigation state tracking
    - Intent continuity across turns
    """
    
    def __init__(self, session_id: str = None, user_id: str = None):
        """Initialize conversation context."""
        self.session_id = session_id or str(uuid.uuid4())
        self.tracer = trace.get_tracer(__name__)
        
        # Core conversation state
        self.metadata = ConversationMetadata(
            session_id=self.session_id,
            user_id=user_id,
            start_time=datetime.now().isoformat(),
            last_activity=datetime.now().isoformat(),
            total_turns=0,
            successful_queries=0,
            failed_queries=0,
            primary_intent="unknown"
        )
        
        # Conversation history
        self.turns: List[ConversationTurn] = []
        
        # Investigation context
        self.investigation = InvestigationContext(
            focus_area="general",
            active_services=[],
            time_range="last 1h",  # Default time range
            key_findings=[]
        )
        
        # Context for follow-up processing
        self.last_query_context = {
            "timeframe": "last 1h",
            "services": [],
            "severity_levels": [],
            "query_type": "unknown"
        }
        
        logger.info(f"💬 Conversation context initialized: {self.session_id}")
    
    def add_turn(self, user_input: str, transcript_confidence: float, 
                 intent: str, generated_query: str, validation_result: Dict[str, Any],
                 response_text: str, query_results: Dict[str, Any] = None) -> str:
        """Add a new turn to the conversation."""
        
        with self.tracer.start_as_current_span(
            "conversation.add_turn",
            attributes={
                "conversation.session_id": self.session_id,
                "conversation.turn_number": len(self.turns) + 1,
                "conversation.intent": intent
            }
        ) as span:
            
            turn_id = f"turn_{len(self.turns) + 1}_{int(time.time())}"
            
            # Create new turn
            turn = ConversationTurn(
                turn_id=turn_id,
                timestamp=datetime.now().isoformat(),
                user_input=user_input,
                transcript_confidence=transcript_confidence,
                intent=intent,
                generated_query=generated_query,
                validation_result=validation_result,
                response_text=response_text,
                query_results=query_results
            )
            
            self.turns.append(turn)
            
            # Update metadata
            self.metadata.total_turns += 1
            self.metadata.last_activity = datetime.now().isoformat()
            
            if validation_result.get("is_valid", False):
                self.metadata.successful_queries += 1
            else:
                self.metadata.failed_queries += 1
            
            # Update primary intent (track most common intent)
            if self.metadata.primary_intent == "unknown":
                self.metadata.primary_intent = intent
            
            # Update investigation context
            self._update_investigation_context(turn)
            
            # Update query context for follow-ups
            self._update_query_context(generated_query, intent)
            
            # Add telemetry
            span.set_attribute("conversation.turn_id", turn_id)
            span.set_attribute("conversation.investigation_focus", self.investigation.focus_area)
            span.set_attribute("conversation.active_services_count", len(self.investigation.active_services))
            
            logger.info(f"💬 Added turn {self.metadata.total_turns}: '{user_input[:30]}...'")
            
            return turn_id
    
    def _update_investigation_context(self, turn: ConversationTurn):
        """Update investigation context based on the latest turn."""
        
        # Extract focus area from intent
        if turn.intent in ["error_analysis", "performance_analysis"]:
            if "error" in turn.intent:
                self.investigation.focus_area = "errors"
            elif "performance" in turn.intent:
                self.investigation.focus_area = "performance"
        
        # Extract services from query if possible
        query_lower = turn.generated_query.lower()
        if "subsystemname" in query_lower or "service" in query_lower:
            # Try to extract service names from the query
            # This is a simplified extraction - could be enhanced
            if "frontend" in query_lower:
                if "frontend" not in self.investigation.active_services:
                    self.investigation.active_services.append("frontend")
            if "backend" in query_lower:
                if "backend" not in self.investigation.active_services:
                    self.investigation.active_services.append("backend")
            if "api" in query_lower:
                if "api" not in self.investigation.active_services:
                    self.investigation.active_services.append("api")
        
        # Extract time range
        if "last" in query_lower:
            if "last 1h" in query_lower or "last hour" in query_lower:
                self.investigation.time_range = "last 1h"
            elif "last 24h" in query_lower or "last day" in query_lower:
                self.investigation.time_range = "last 24h"
            elif "last 1d" in query_lower:
                self.investigation.time_range = "last 1d"
    
    def _update_query_context(self, query: str, intent: str):
        """Update the last query context for follow-up processing."""
        
        query_lower = query.lower()
        
        # Extract timeframe
        if "last 1h" in query_lower:
            self.last_query_context["timeframe"] = "last 1h"
        elif "last 24h" in query_lower or "last 1d" in query_lower:
            self.last_query_context["timeframe"] = "last 24h"
        elif "last 7d" in query_lower:
            self.last_query_context["timeframe"] = "last 7d"
        
        # Extract query type
        if "filter" in query_lower and "error" in query_lower:
            self.last_query_context["query_type"] = "error_filtering"
        elif "groupby" in query_lower:
            self.last_query_context["query_type"] = "aggregation"
        elif "top" in query_lower:
            self.last_query_context["query_type"] = "ranking"
        
        self.last_query_context["intent"] = intent
    
    def enhance_follow_up_query(self, user_input: str) -> Tuple[str, Dict[str, Any]]:
        """
        Enhance follow-up queries with conversation context.
        
        Handles queries like:
        - "what about yesterday?"
        - "show me just the frontend errors"
        - "what about the last 24 hours?"
        """
        
        with self.tracer.start_as_current_span(
            "conversation.enhance_follow_up",
            attributes={
                "conversation.session_id": self.session_id,
                "conversation.original_query": user_input,
                "conversation.has_context": len(self.turns) > 0
            }
        ) as span:
            
            enhanced_query = user_input
            context_applied = {}
            
            if len(self.turns) == 0:
                # No previous context
                return enhanced_query, context_applied
            
            last_turn = self.turns[-1]
            user_input_lower = user_input.lower()
            
            # Handle temporal references
            if any(phrase in user_input_lower for phrase in ["yesterday", "last day", "24 hours"]):
                enhanced_query = enhanced_query.replace("yesterday", "last 24h")
                enhanced_query = enhanced_query.replace("last day", "last 24h")
                enhanced_query = enhanced_query.replace("24 hours", "last 24h")
                context_applied["temporal_expansion"] = "last 24h"
            
            # Handle "what about" patterns
            if user_input_lower.startswith("what about"):
                # Inherit context from previous query
                base_context = f"Show me {self.investigation.focus_area}"
                if self.investigation.active_services:
                    base_context += f" from {', '.join(self.investigation.active_services)}"
                
                # Replace "what about" with context
                enhanced_query = user_input_lower.replace("what about", base_context)
                context_applied["context_inheritance"] = {
                    "focus_area": self.investigation.focus_area,
                    "services": self.investigation.active_services
                }
            
            # Handle service-specific follow-ups
            if "just the" in user_input_lower and len(self.investigation.active_services) > 1:
                # User wants to narrow down to specific service
                for service in ["frontend", "backend", "api", "database"]:
                    if service in user_input_lower:
                        enhanced_query += f" from {service} service"
                        context_applied["service_focus"] = service
                        break
            
            # Apply time range context if not specified
            if "last" not in user_input_lower and "between" not in user_input_lower:
                enhanced_query += f" {self.investigation.time_range}"
                context_applied["default_timeframe"] = self.investigation.time_range
            
            # Add telemetry
            span.set_attribute("conversation.enhanced_query", enhanced_query)
            span.set_attribute("conversation.context_applied", str(context_applied))
            
            logger.info(f"💬 Enhanced follow-up: '{user_input}' → '{enhanced_query}'")
            
            return enhanced_query, context_applied
    
    def get_conversation_summary(self) -> Dict[str, Any]:
        """Get a summary of the current conversation."""
        
        return {
            "session_id": self.session_id,
            "metadata": asdict(self.metadata),
            "investigation": asdict(self.investigation),
            "recent_turns": [
                {
                    "user_input": turn.user_input,
                    "intent": turn.intent,
                    "timestamp": turn.timestamp,
                    "success": turn.validation_result.get("is_valid", False)
                }
                for turn in self.turns[-3:]  # Last 3 turns
            ],
            "query_context": self.last_query_context
        }
    
    def is_expired(self, timeout_minutes: int = 30) -> bool:
        """Check if conversation has expired due to inactivity."""
        
        if not self.metadata.last_activity:
            return True
        
        last_activity = datetime.fromisoformat(self.metadata.last_activity.replace('Z', '+00:00'))
        expiry_time = last_activity + timedelta(minutes=timeout_minutes)
        
        return datetime.now() > expiry_time.replace(tzinfo=None)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert conversation context to dictionary for serialization."""
        
        return {
            "session_id": self.session_id,
            "metadata": asdict(self.metadata),
            "investigation": asdict(self.investigation),
            "turns": [asdict(turn) for turn in self.turns],
            "last_query_context": self.last_query_context
        }


class ConversationManager:
    """Manages multiple conversation contexts and session lifecycle."""
    
    def __init__(self):
        """Initialize conversation manager."""
        self.sessions: Dict[str, ConversationContext] = {}
        self.tracer = trace.get_tracer(__name__)
        logger.info("💬 ConversationManager initialized")
    
    def get_or_create_context(self, session_id: str = None, user_id: str = None) -> ConversationContext:
        """Get existing conversation context or create new one."""
        
        if session_id and session_id in self.sessions:
            context = self.sessions[session_id]
            
            # Check if session has expired
            if context.is_expired():
                logger.info(f"💬 Session {session_id} expired, creating new context")
                del self.sessions[session_id]
                context = ConversationContext(session_id=session_id, user_id=user_id)
                self.sessions[session_id] = context
            
            return context
        
        # Create new context
        context = ConversationContext(session_id=session_id, user_id=user_id)
        self.sessions[context.session_id] = context
        
        logger.info(f"💬 Created new conversation context: {context.session_id}")
        return context
    
    def cleanup_expired_sessions(self, timeout_minutes: int = 30):
        """Clean up expired conversation sessions."""
        
        expired_sessions = [
            session_id for session_id, context in self.sessions.items()
            if context.is_expired(timeout_minutes)
        ]
        
        for session_id in expired_sessions:
            del self.sessions[session_id]
            logger.info(f"💬 Cleaned up expired session: {session_id}")
        
        if expired_sessions:
            logger.info(f"💬 Cleaned up {len(expired_sessions)} expired sessions")
    
    def get_session_count(self) -> int:
        """Get current number of active sessions."""
        return len(self.sessions)
    
    def get_all_sessions_summary(self) -> List[Dict[str, Any]]:
        """Get summary of all active sessions."""
        
        return [
            {
                "session_id": session_id,
                "turns": context.metadata.total_turns,
                "last_activity": context.metadata.last_activity,
                "focus_area": context.investigation.focus_area
            }
            for session_id, context in self.sessions.items()
        ]


# Global conversation manager instance
conversation_manager = ConversationManager() 