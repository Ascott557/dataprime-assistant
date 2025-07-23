"""Tests for DataPrime Assistant functionality."""

import pytest
from unittest.mock import Mock, patch, MagicMock
import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from dataprime_assistant import DataPrimeAssistant
from knowledge_base import IntentType, IntentResult
from utils.validation import ValidationResult, ValidationLevel, ValidationIssue

class TestDataPrimeAssistant:
    """Test suite for DataPrime Assistant."""
    
    @pytest.fixture
    def mock_config(self):
        """Mock configuration."""
        with patch('dataprime_assistant.get_config') as mock:
            config = Mock()
            config.openai_api_key = "test-key"
            config.model_name = "gpt-4o-mini"
            config.max_tokens = 1000
            config.temperature = 0.1
            config.service_name = "test-service"
            mock.return_value = config
            yield config
    
    @pytest.fixture
    def mock_openai_client(self):
        """Mock OpenAI client."""
        with patch('dataprime_assistant.OpenAI') as mock:
            client = Mock()
            response = Mock()
            response.choices = [Mock()]
            response.choices[0].message.content = "source logs last 1h | filter $m.severity == 'Error'"
            client.chat.completions.create.return_value = response
            mock.return_value = client
            yield client
    
    @pytest.fixture
    def mock_tracer(self):
        """Mock OpenTelemetry tracer."""
        with patch('dataprime_assistant.trace.get_tracer') as mock:
            tracer = Mock()
            span = Mock()
            span.__enter__ = Mock(return_value=span)
            span.__exit__ = Mock(return_value=None)
            tracer.start_as_current_span.return_value = span
            mock.return_value = tracer
            yield tracer
    
    @pytest.fixture
    def assistant(self, mock_config, mock_openai_client, mock_tracer):
        """Create assistant instance with mocked dependencies."""
        with patch('dataprime_assistant.initialize_instrumentation'):
            assistant = DataPrimeAssistant()
            return assistant
    
    def test_intent_classification(self, assistant):
        """Test intent classification for different query types."""
        
        test_cases = [
            ("Show me errors from last hour", IntentType.ERROR_ANALYSIS),
            ("Find slow queries", IntentType.PERFORMANCE),
            ("Count logs by service", IntentType.AGGREGATION),
            ("Show me logs from payment service", IntentType.SEARCH),
            ("Hourly error trends", IntentType.TIME_ANALYSIS),
        ]
        
        for user_input, expected_intent in test_cases:
            intent = assistant._classify_intent(user_input)
            assert intent.intent_type == expected_intent
            assert 0 <= intent.confidence <= 1
            assert isinstance(intent.keywords_found, list)
    
    def test_query_generation_success(self, assistant):
        """Test successful query generation."""
        
        user_input = "Show me errors from the last hour"
        result = assistant.generate_query(user_input)
        
        # Check result structure
        assert "user_input" in result
        assert "generated_query" in result
        assert "intent" in result
        assert "validation" in result
        assert "generation_time" in result
        
        # Check intent analysis
        intent = result["intent"]
        assert intent["type"] == "error_analysis"
        assert isinstance(intent["confidence"], float)
        assert isinstance(intent["keywords"], list)
        
        # Check validation
        validation = result["validation"]
        assert "is_valid" in validation
        assert "syntax_score" in validation
        assert "complexity_score" in validation
    
    def test_query_validation(self, assistant):
        """Test query validation functionality."""
        
        # Test valid query
        valid_query = "source logs last 1h | filter $m.severity == 'Error'"
        validation = assistant._validate_query(valid_query)
        
        assert validation.is_valid == True
        assert validation.syntax_score >= 0.8
        assert len([issue for issue in validation.issues if issue.level == ValidationLevel.ERROR]) == 0
        
        # Test invalid query
        invalid_query = "invalid syntax here"
        validation = assistant._validate_query(invalid_query)
        
        assert validation.is_valid == False
        assert validation.syntax_score < 1.0
        assert len([issue for issue in validation.issues if issue.level == ValidationLevel.ERROR]) > 0
    
    def test_error_handling(self, assistant):
        """Test error handling in query generation."""
        
        with patch.object(assistant.openai_client.chat.completions, 'create') as mock_create:
            mock_create.side_effect = Exception("API Error")
            
            result = assistant.generate_query("test input")
            
            assert "error" in result
            assert "trace_context" in result
    
    def test_feedback_recording(self, assistant):
        """Test feedback recording functionality."""
        
        query_result = {
            "user_input": "test input",
            "generated_query": "source logs",
            "validation": {"syntax_score": 0.9}
        }
        
        # Should not raise exception
        assistant.record_feedback(query_result, 5, "Great result!")
    
    def test_query_explanation(self, assistant):
        """Test query explanation functionality."""
        
        query = "source logs last 1h | filter $m.severity == 'Error'"
        
        with patch.object(assistant.openai_client.chat.completions, 'create') as mock_create:
            response = Mock()
            response.choices = [Mock()]
            response.choices[0].message.content = "This query finds all error logs from the last hour."
            mock_create.return_value = response
            
            explanation = assistant.explain_query(query)
            
            assert "explanation" in explanation
            assert "validation" in explanation
            assert explanation["query"] == query

class TestIntentClassification:
    """Test intent classification functionality."""
    
    @pytest.fixture
    def classifier(self):
        from knowledge_base import IntentClassifier
        return IntentClassifier()
    
    def test_error_analysis_intent(self, classifier):
        """Test error analysis intent detection."""
        
        test_inputs = [
            "Show me all errors",
            "Find failed requests",
            "Display exception logs",
            "Get crash reports"
        ]
        
        for user_input in test_inputs:
            result = classifier.classify(user_input)
            assert result.intent_type == IntentType.ERROR_ANALYSIS
            assert result.confidence > 0
    
    def test_performance_intent(self, classifier):
        """Test performance analysis intent detection."""
        
        test_inputs = [
            "Find slow queries",
            "Show high latency requests",
            "Get timeout errors",
            "Display performance issues"
        ]
        
        for user_input in test_inputs:
            result = classifier.classify(user_input)
            assert result.intent_type == IntentType.PERFORMANCE
            assert result.confidence > 0
    
    def test_aggregation_intent(self, classifier):
        """Test aggregation intent detection."""
        
        test_inputs = [
            "Count logs by service",
            "Sum total requests",
            "Average response time",
            "Group by application"
        ]
        
        for user_input in test_inputs:
            result = classifier.classify(user_input)
            assert result.intent_type == IntentType.AGGREGATION
            assert result.confidence > 0
    
    def test_timeframe_extraction(self, classifier):
        """Test timeframe extraction from user input."""
        
        test_cases = [
            ("last 2 hours", "last 2h"),
            ("yesterday", "between @'now'-1d and @'now'"),
            ("last 30 minutes", "last 30m"),
            ("past 5 days", "last 5d")
        ]
        
        for user_input, expected_timeframe in test_cases:
            timeframe = classifier._extract_timeframe(f"Show errors {user_input}")
            assert timeframe == expected_timeframe
    
    def test_entity_extraction(self, classifier):
        """Test entity extraction from user input."""
        
        test_cases = [
            ("errors from the payment service", {"service": "payment"}),
            ("logs in the user-api application", {"service": "user-api"}),
            ("status code 404 errors", {"status_code": 404}),
            ("endpoint /api/users problems", {"endpoint": "/api/users"})
        ]
        
        for user_input, expected_entities in test_cases:
            entities = classifier._extract_entities(user_input)
            for key, value in expected_entities.items():
                assert entities.get(key) == value

class TestQueryValidation:
    """Test query validation functionality."""
    
    @pytest.fixture
    def validator(self):
        from utils.validation import DataPrimeValidator
        return DataPrimeValidator()
    
    def test_valid_query_structure(self, validator):
        """Test validation of properly structured queries."""
        
        valid_queries = [
            "source logs",
            "source logs last 1h",
            "source logs | filter $m.severity == 'Error'",
            "source logs | groupby $l.subsystemname aggregate count()",
            "source logs | filter $d.status_code >= 400 | top 10 by $d.response_time"
        ]
        
        for query in valid_queries:
            result = validator.validate(query)
            assert result.is_valid == True
            assert result.syntax_score >= 0.8
    
    def test_invalid_query_structure(self, validator):
        """Test validation of improperly structured queries."""
        
        invalid_queries = [
            "",  # Empty query
            "filter $m.severity == 'Error'",  # Missing source
            "source logs |",  # Incomplete pipe
            "source logs | invalid_operator",  # Unknown operator
            "source logs | filter unmatched_quotes'"  # Syntax error
        ]
        
        for query in invalid_queries:
            result = validator.validate(query)
            assert result.is_valid == False
            assert len([issue for issue in result.issues if issue.level == ValidationLevel.ERROR]) > 0
    
    def test_field_reference_validation(self, validator):
        """Test validation of field references."""
        
        # Valid field references
        valid_query = "source logs | filter $m.severity == 'Error' && $d.response_time > 1000"
        result = validator.validate(valid_query)
        field_errors = [issue for issue in result.issues if "field" in issue.message.lower()]
        assert len(field_errors) == 0
        
        # Invalid field references
        invalid_query = "source logs | filter $x.invalid_prefix == 'test'"
        result = validator.validate(invalid_query)
        field_errors = [issue for issue in result.issues if "field" in issue.message.lower()]
        assert len(field_errors) > 0
    
    def test_performance_analysis(self, validator):
        """Test performance warning detection."""
        
        # Query without time filter should trigger warning
        slow_query = "source logs | filter $d.message ~~ 'search_term'"
        result = validator.validate(slow_query)
        assert len(result.performance_warnings) > 0
        
        # Query with time filter should have fewer warnings
        fast_query = "source logs last 1h | filter $d.message ~~ 'search_term'"
        result = validator.validate(fast_query)
        # Should have fewer or different warnings
        assert isinstance(result.performance_warnings, list)
    
    def test_complexity_calculation(self, validator):
        """Test query complexity scoring."""
        
        simple_query = "source logs"
        complex_query = "source logs | filter $m.severity == 'Error' | groupby $l.subsystemname aggregate count() | top 10 by count()"
        
        simple_result = validator.validate(simple_query)
        complex_result = validator.validate(complex_query)
        
        assert simple_result.complexity_score < complex_result.complexity_score
        assert 0 <= simple_result.complexity_score <= 1
        assert 0 <= complex_result.complexity_score <= 1

class TestKnowledgeBase:
    """Test knowledge base functionality."""
    
    @pytest.fixture
    def knowledge_base(self):
        from knowledge_base import DataPrimeKnowledgeBase
        return DataPrimeKnowledgeBase()
    
    def test_example_retrieval(self, knowledge_base):
        """Test retrieval of relevant examples."""
        
        intent = IntentResult(
            intent_type=IntentType.ERROR_ANALYSIS,
            confidence=0.8,
            keywords_found=["error", "show"]
        )
        
        examples = knowledge_base.get_relevant_examples(intent, limit=3)
        
        assert len(examples) <= 3
        assert all(ex.intent_type == IntentType.ERROR_ANALYSIS for ex in examples)
        assert all(hasattr(ex, 'user_input') for ex in examples)
        assert all(hasattr(ex, 'dataprime_query') for ex in examples)
    
    def test_context_prompt_building(self, knowledge_base):
        """Test context prompt construction."""
        
        intent = IntentResult(
            intent_type=IntentType.ERROR_ANALYSIS,
            confidence=0.8,
            keywords_found=["error"],
            suggested_timeframe="last 1h"
        )
        
        examples = knowledge_base.get_relevant_examples(intent, limit=2)
        prompt = knowledge_base.build_context_prompt("Show me errors", intent, examples)
        
        assert "error_analysis" in prompt
        assert "last 1h" in prompt
        assert len(examples) <= 2
        assert all(ex.user_input in prompt for ex in examples)
    
    def test_query_suggestions(self, knowledge_base):
        """Test query completion suggestions."""
        
        suggestions = knowledge_base.get_query_suggestions("")
        assert len(suggestions) > 0
        assert all("source" in suggestion for suggestion in suggestions)
        
        suggestions = knowledge_base.get_query_suggestions("source logs")
        assert len(suggestions) > 0
        assert all("source logs" in suggestion for suggestion in suggestions)

if __name__ == "__main__":
    pytest.main([__file__])