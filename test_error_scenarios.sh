#!/bin/bash

# Error Path Testing Script for DataPrime Assistant
# This script demonstrates various error scenarios for observability testing

set -e

BASE_URL="http://localhost:8000"
TIMESTAMP=$(date +%s)

echo "🔥 DataPrime Assistant - Error Scenario Testing"
echo "================================================"
echo "Timestamp: $TIMESTAMP"
echo "Base URL: $BASE_URL"
echo ""

# Test 1: OpenAI API Timeout/Rate Limiting Simulation
echo "🧪 Test 1: OpenAI API Stress Testing (Rate Limiting)"
echo "----------------------------------------------------"

RATE_LIMIT_TRACE="ratelimit${TIMESTAMP}123456789012345"

# Send rapid requests to potentially trigger rate limiting
for i in {1..15}; do
    SPAN_ID=$(printf "%016d" $i)
    echo "Sending request $i/15..."
    
    curl -s -X POST "$BASE_URL/api/generate-query" \
        -H "Content-Type: application/json" \
        -H "traceparent: 00-${RATE_LIMIT_TRACE}-${SPAN_ID}-01" \
        -d "{\"user_input\": \"Rate limit test request $i - show me authentication errors\"}" \
        -w "Status: %{http_code}, Time: %{time_total}s\n" \
        -o /dev/null &
    
    # Small delay to prevent overwhelming the system
    sleep 0.1
done

echo "Waiting for rate limit requests to complete..."
wait
echo "✅ Rate limit test completed"
echo ""

# Test 2: Database Concurrency Issues
echo "🧪 Test 2: Database Lock Testing (Concurrent Feedback)"
echo "-------------------------------------------------------"

DB_LOCK_TRACE="dblock${TIMESTAMP}567890123456789"

# Create concurrent feedback submissions to trigger database locks
for i in {1..25}; do
    SPAN_ID=$(printf "%016d" $i)
    echo "Submitting concurrent feedback $i/25..."
    
    curl -s -X POST "$BASE_URL/api/feedback" \
        -H "Content-Type: application/json" \
        -H "traceparent: 00-${DB_LOCK_TRACE}-${SPAN_ID}-01" \
        -d "{
            \"session_id\": \"concurrent-test-${i}\",
            \"feedback_type\": \"thumbs_up\",
            \"user_input\": \"Database concurrency test $i\",
            \"query_text\": \"source logs | filter \$m.severity == 'Error'\"
        }" \
        -w "Status: %{http_code}, Time: %{time_total}s\n" \
        -o /dev/null &
    
    # No delay to maximize concurrency
done

echo "Waiting for concurrent feedback submissions..."
wait
echo "✅ Database concurrency test completed"
echo ""

# Test 3: Invalid Trace Context Scenarios
echo "🧪 Test 3: Trace Context Validation Testing"
echo "--------------------------------------------"

CONTEXT_TESTS=(
    # Test case format: "description|traceparent_header"
    "Invalid version|01-12345678901234567890123456789012-1111222233334444-01"
    "Short trace ID|00-1234567890123456789012345678901-1111222233334444-01"
    "Invalid hex chars|00-12345678901234567890123456789012-11112222333344gg-01"
    "All-zero trace ID|00-00000000000000000000000000000000-1111222233334444-01"
    "All-zero span ID|00-12345678901234567890123456789012-0000000000000000-01"
    "Missing parts|00-12345678901234567890123456789012-1111222233334444"
    "Extra parts|00-12345678901234567890123456789012-1111222233334444-01-extra"
    "Non-hex version|xx-12345678901234567890123456789012-1111222233334444-01"
)

for test_case in "${CONTEXT_TESTS[@]}"; do
    IFS='|' read -r description traceparent <<< "$test_case"
    echo "Testing: $description"
    
    curl -s -X POST "$BASE_URL/api/generate-query" \
        -H "Content-Type: application/json" \
        -H "traceparent: $traceparent" \
        -d '{"user_input": "Context validation test"}' \
        -w "Status: %{http_code}\n" \
        -o /dev/null
done

echo "✅ Context validation tests completed"
echo ""

# Test 4: Cascade Failure Simulation
echo "🧪 Test 4: Cascade Failure Testing"
echo "-----------------------------------"

CASCADE_TRACE="cascade${TIMESTAMP}890123456789012"

# Test empty input (should trigger validation failures)
echo "Testing empty input (validation failure)..."
curl -s -X POST "$BASE_URL/api/generate-query" \
    -H "Content-Type: application/json" \
    -H "traceparent: 00-${CASCADE_TRACE}-1111222233334444-01" \
    -d '{"user_input": ""}' \
    -w "Status: %{http_code}\n" | jq -r '.error // "Success"'

# Test very long input (might trigger token limits)
echo "Testing very long input (potential token limit)..."
LONG_INPUT="Show me all authentication errors and security issues and performance problems and database errors and network timeouts and API failures and system crashes and memory leaks and disk space issues and CPU spikes and load balancing problems and SSL certificate errors and DNS resolution failures and connection timeouts and rate limiting issues and quota exceeded errors and permission denied errors and file not found errors and configuration errors and dependency failures and service unavailable errors and internal server errors"

curl -s -X POST "$BASE_URL/api/generate-query" \
    -H "Content-Type: application/json" \
    -H "traceparent: 00-${CASCADE_TRACE}-2222333344445555-01" \
    -d "{\"user_input\": \"$LONG_INPUT\"}" \
    -w "Status: %{http_code}\n" | jq -r '.error // .query[:50] + "..." // "Success"'

echo "✅ Cascade failure tests completed"
echo ""

# Test 5: Recovery Pattern Testing
echo "🧪 Test 5: Recovery Pattern Testing"
echo "------------------------------------"

RECOVERY_TRACE="recovery${TIMESTAMP}234567890123456"

# Test feedback submission after query (normal flow)
echo "Testing normal query -> feedback flow..."
QUERY_RESPONSE=$(curl -s -X POST "$BASE_URL/api/generate-query" \
    -H "Content-Type: application/json" \
    -H "traceparent: 00-${RECOVERY_TRACE}-1111111111111111-01" \
    -d '{"user_input": "Show me recent errors"}')

QUERY_TRACE_ID=$(echo "$QUERY_RESPONSE" | jq -r '.trace_id')
echo "Query trace ID: $QUERY_TRACE_ID"

# Submit feedback using the same trace
FEEDBACK_RESPONSE=$(curl -s -X POST "$BASE_URL/api/feedback" \
    -H "Content-Type: application/json" \
    -H "traceparent: 00-${RECOVERY_TRACE}-2222222222222222-01" \
    -d '{
        "session_id": "recovery-test",
        "feedback_type": "thumbs_up",
        "user_input": "Show me recent errors", 
        "query_text": "source logs | filter $m.severity == \"Error\""
    }')

FEEDBACK_TRACE_ID=$(echo "$FEEDBACK_RESPONSE" | jq -r '.trace_id')
echo "Feedback trace ID: $FEEDBACK_TRACE_ID"

if [ "$QUERY_TRACE_ID" = "$FEEDBACK_TRACE_ID" ]; then
    echo "✅ SUCCESS: Trace correlation working correctly"
else
    echo "⚠️  WARNING: Trace correlation may have issues"
fi

echo "✅ Recovery pattern tests completed"
echo ""

# Test 6: Slow Database Performance Demo
echo "🧪 Test 6: Slow Database Performance Demo"
echo "------------------------------------------"

SLOW_DB_TRACE="slowdb${TIMESTAMP}345678901234567"

echo "Testing slow database operation demo..."
curl -s -X POST "$BASE_URL/api/demo/slow-db" \
    -H "Content-Type: application/json" \
    -H "traceparent: 00-${SLOW_DB_TRACE}-1111111111111111-01" \
    -w "Status: %{http_code}, Time: %{time_total}s\n" | jq -r '.message // .error'

echo "✅ Slow database demo test completed"
echo ""

# Summary
echo "🎉 Error Scenario Testing Complete"
echo "=================================="
echo "Total traces generated: ~70"
echo "Test categories covered:"
echo "  - Rate limiting and API timeouts"
echo "  - Database concurrency and locks"
echo "  - Trace context validation"
echo "  - Cascade failure patterns"
echo "  - Recovery and correlation"
echo "  - Performance analysis (slow database)"
echo ""
echo "🔍 Check Coralogix for detailed trace analysis:"
echo "  - Search for traces with IDs containing: $TIMESTAMP"
echo "  - Look for error status codes and exception details"
echo "  - Analyze span relationships and timing"
echo "  - Review attribute-based filtering capabilities"
echo "  - Check slow database spans for performance insights"
echo ""
echo "📊 Recommended Coralogix queries:"
echo "  source spans | filter \$d.trace_id contains '$TIMESTAMP'"
echo "  source spans | filter \$m.status_code == 'ERROR' and \$timestamp > now() - 10m"
echo "  source spans | filter \$d.pipeline exists and \$d.pipeline.success == false"
echo "  source spans | filter \$d.demo.type == 'slow_database' and \$d.duration > 1000"
