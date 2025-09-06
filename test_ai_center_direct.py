#!/usr/bin/env python3
"""
Direct test to verify AI Center traces are being sent to Coralogix
"""
import os
import time
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_ai_center_direct():
    """Test AI Center integration directly."""
    print("🧪 DIRECT AI CENTER TEST")
    print("=" * 50)
    
    try:
        # Import and initialize llm_tracekit directly
        from llm_tracekit import OpenAIInstrumentor, setup_export_to_coralogix
        from openai import OpenAI
        from opentelemetry import trace
        
        print("✅ All imports successful")
        
        # Setup Coralogix export with exact same config as working monolithic app
        print("🔧 Setting up Coralogix export...")
        setup_export_to_coralogix(
            service_name="dataprime_assistant",
            application_name="ai-dataprime", 
            subsystem_name="query-generator",
            coralogix_token=os.getenv('CX_TOKEN'),
            coralogix_endpoint=os.getenv('CX_ENDPOINT'),
            capture_content=True
        )
        print("✅ Coralogix export configured")
        
        # Initialize OpenAI instrumentation
        OpenAIInstrumentor().instrument()
        print("✅ OpenAI instrumentation enabled")
        
        # Initialize OpenAI client
        openai_client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        print("✅ OpenAI client initialized")
        
        # Create a tracer
        tracer = trace.get_tracer("ai_center_test")
        
        # Make a test OpenAI call with explicit tracing
        print("🚀 Making test OpenAI call...")
        with tracer.start_as_current_span("ai_center_test_call") as span:
            span.set_attribute("test.name", "ai_center_direct_test")
            span.set_attribute("test.timestamp", str(time.time()))
            span.set_attribute("business.use_case", "ai_center_verification")
            
            response = openai_client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "You are a test assistant."},
                    {"role": "user", "content": "Generate a simple DataPrime query for AI Center testing"}
                ],
                max_tokens=50,
                temperature=0.3
            )
            
            generated_query = response.choices[0].message.content.strip()
            
            span.set_attribute("ai.response.content", generated_query[:100])
            span.set_attribute("ai.tokens.total", response.usage.total_tokens)
            span.set_attribute("test.success", True)
            
            print(f"✅ OpenAI call successful!")
            print(f"📝 Generated query: {generated_query}")
            print(f"🔢 Tokens used: {response.usage.total_tokens}")
            print(f"🆔 Trace ID: {format(span.get_span_context().trace_id, '032x')}")
            print(f"🆔 Span ID: {format(span.get_span_context().span_id, '016x')}")
            
        print("\n🎯 TEST COMPLETED SUCCESSFULLY!")
        print("=" * 50)
        print("📊 EXPECTED IN CORALOGIX AI CENTER:")
        print("   • Service: dataprime_assistant")
        print("   • Application: ai-dataprime") 
        print("   • Subsystem: query-generator")
        print("   • LLM traces with GPT-4o calls")
        print("   • Prompt and response content")
        print("   • Token usage metrics")
        print("\n⏰ Check your Coralogix AI Center in 30-60 seconds!")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        print(f"📋 Full error trace: {traceback.format_exc()}")
        return False

if __name__ == "__main__":
    test_ai_center_direct()
