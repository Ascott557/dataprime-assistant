#!/usr/bin/env python3
"""
🎙️ Voice Processing Handler for DataPrime Assistant

Handles speech-to-text (OpenAI Whisper) and text-to-speech (OpenAI TTS) 
for voice-driven observability interactions.
"""

import os
import io
import asyncio
import tempfile
from datetime import datetime
from typing import Optional, Dict, Any, AsyncGenerator
from openai import AsyncOpenAI
from opentelemetry import trace
import logging

logger = logging.getLogger(__name__)

class VoiceHandler:
    """Handles voice processing with OpenAI Whisper and TTS."""
    
    def __init__(self, openai_client: Optional[AsyncOpenAI] = None):
        """Initialize voice handler with OpenAI client."""
        self.client = openai_client or AsyncOpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        self.tracer = trace.get_tracer(__name__)
        
        # Voice processing settings
        self.whisper_model = "whisper-1"
        self.tts_model = "tts-1"  # Use tts-1 for faster responses
        self.tts_voice = "alloy"  # Good for conversational AI
        
        logger.info("✅ VoiceHandler initialized")
    
    async def speech_to_text(self, audio_data: bytes, session_id: str = None) -> Dict[str, Any]:
        """
        Convert speech audio to text using OpenAI Whisper.
        
        Args:
            audio_data: Raw audio bytes (WebM, MP3, WAV, etc.)
            session_id: Optional session ID for tracking
            
        Returns:
            Dict with transcript, confidence, and metadata
        """
        with self.tracer.start_as_current_span(
            "voice.speech_to_text",
            attributes={
                "voice.model": self.whisper_model,
                "voice.session_id": session_id or "unknown",
                "voice.audio_size_bytes": len(audio_data)
            }
        ) as span:
            try:
                # Create temporary file for audio data
                with tempfile.NamedTemporaryFile(suffix=".webm", delete=False) as temp_file:
                    temp_file.write(audio_data)
                    temp_file.flush()
                    
                    # Transcribe using OpenAI Whisper
                    with open(temp_file.name, "rb") as audio_file:
                        transcript_response = await self.client.audio.transcriptions.create(
                            model=self.whisper_model,
                            file=audio_file,
                            response_format="verbose_json",  # Get confidence and timing
                            language="en"  # Optimize for English observability queries
                        )
                
                # Clean up temp file
                os.unlink(temp_file.name)
                
                transcript = transcript_response.text.strip()
                
                # Add telemetry attributes
                span.set_attribute("voice.transcript", transcript)
                span.set_attribute("voice.transcript_length", len(transcript))
                span.set_attribute("voice.language", transcript_response.language or "en")
                span.set_attribute("voice.duration", getattr(transcript_response, 'duration', 0))
                
                result = {
                    "success": True,
                    "transcript": transcript,
                    "language": transcript_response.language or "en",
                    "duration": getattr(transcript_response, 'duration', 0),
                    "timestamp": datetime.now().isoformat(),
                    "session_id": session_id
                }
                
                logger.info(f"🎙️ Speech-to-text completed: '{transcript[:50]}...'")
                return result
                
            except Exception as e:
                span.set_attribute("error.type", type(e).__name__)
                span.set_attribute("error.message", str(e))
                
                logger.error(f"❌ Speech-to-text failed: {e}")
                return {
                    "success": False,
                    "error": str(e),
                    "timestamp": datetime.now().isoformat(),
                    "session_id": session_id
                }
    
    async def text_to_speech(self, text: str, session_id: str = None) -> Dict[str, Any]:
        """
        Convert text to speech using OpenAI TTS.
        
        Args:
            text: Text to convert to speech
            session_id: Optional session ID for tracking
            
        Returns:
            Dict with audio data and metadata
        """
        with self.tracer.start_as_current_span(
            "voice.text_to_speech",
            attributes={
                "voice.tts_model": self.tts_model,
                "voice.voice": self.tts_voice,
                "voice.session_id": session_id or "unknown",
                "voice.text_length": len(text)
            }
        ) as span:
            try:
                # Add telemetry for the text being spoken
                span.set_attribute("voice.text_snippet", text[:100])
                
                # Generate speech using OpenAI TTS
                response = await self.client.audio.speech.create(
                    model=self.tts_model,
                    voice=self.tts_voice,
                    input=text,
                    response_format="mp3"  # Good compression for web
                )
                
                # Get audio bytes
                audio_bytes = response.content
                
                # Add telemetry attributes
                span.set_attribute("voice.audio_size_bytes", len(audio_bytes))
                span.set_attribute("voice.generation_success", True)
                
                result = {
                    "success": True,
                    "audio_data": audio_bytes,
                    "format": "mp3",
                    "size_bytes": len(audio_bytes),
                    "text_length": len(text),
                    "timestamp": datetime.now().isoformat(),
                    "session_id": session_id
                }
                
                logger.info(f"🔊 Text-to-speech completed: {len(audio_bytes)} bytes")
                return result
                
            except Exception as e:
                span.set_attribute("error.type", type(e).__name__)
                span.set_attribute("error.message", str(e))
                span.set_attribute("voice.generation_success", False)
                
                logger.error(f"❌ Text-to-speech failed: {e}")
                return {
                    "success": False,
                    "error": str(e),
                    "timestamp": datetime.now().isoformat(),
                    "session_id": session_id
                }
    
    async def process_voice_query(self, audio_data: bytes, session_id: str, 
                                conversation_context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Complete voice processing pipeline: speech-to-text -> query processing -> text-to-speech.
        
        This is the main entry point for voice interactions.
        """
        with self.tracer.start_as_current_span(
            "voice.process_complete_interaction",
            attributes={
                "voice.session_id": session_id,
                "voice.has_context": bool(conversation_context)
            }
        ) as span:
            try:
                # Step 1: Convert speech to text
                stt_result = await self.speech_to_text(audio_data, session_id)
                if not stt_result["success"]:
                    return {
                        "success": False,
                        "stage": "speech_to_text",
                        "error": stt_result["error"]
                    }
                
                transcript = stt_result["transcript"]
                span.set_attribute("voice.user_query", transcript)
                
                # Step 2: Process the query (will be handled by external logic)
                # This method returns the transcript for further processing
                return {
                    "success": True,
                    "stage": "speech_to_text_complete",
                    "transcript": transcript,
                    "stt_metadata": stt_result,
                    "ready_for_query_processing": True
                }
                
            except Exception as e:
                span.set_attribute("error.type", type(e).__name__)
                span.set_attribute("error.message", str(e))
                
                logger.error(f"❌ Voice processing pipeline failed: {e}")
                return {
                    "success": False,
                    "stage": "pipeline_error",
                    "error": str(e)
                }
    
    async def generate_voice_response(self, response_text: str, session_id: str) -> Dict[str, Any]:
        """
        Generate voice response for query results.
        
        This should be called after query processing is complete.
        """
        with self.tracer.start_as_current_span(
            "voice.generate_response",
            attributes={
                "voice.session_id": session_id,
                "voice.response_length": len(response_text)
            }
        ) as span:
            
            # Convert response to speech
            tts_result = await self.text_to_speech(response_text, session_id)
            
            if tts_result["success"]:
                span.set_attribute("voice.response_generated", True)
                return {
                    "success": True,
                    "response_text": response_text,
                    "audio_data": tts_result["audio_data"],
                    "audio_format": tts_result["format"],
                    "audio_size": tts_result["size_bytes"]
                }
            else:
                span.set_attribute("voice.response_generated", False)
                return {
                    "success": False,
                    "error": tts_result["error"],
                    "fallback_text": response_text
                }

def create_voice_handler() -> VoiceHandler:
    """Factory function to create voice handler with proper async client."""
    try:
        # Create async OpenAI client
        async_client = AsyncOpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        return VoiceHandler(async_client)
    except Exception as e:
        logger.error(f"❌ Failed to create voice handler: {e}")
        raise 