#!/bin/bash
# Test vLLM distributed inference server

PORT=${1:-8000}
MODEL="deepseek-ai/DeepSeek-R1-Distill-Llama-8B"
BASE_URL="http://localhost:$PORT"

echo "=== Testing vLLM Server ==="
echo "URL: $BASE_URL"
echo ""

# Health check - use HTTP status code since body is empty
echo "1. Health Check"
echo "----------------"
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "$BASE_URL/health" 2>/dev/null)
if [ "$HTTP_CODE" != "200" ]; then
    echo "ERROR: Server not responding (HTTP $HTTP_CODE)"
    echo ""
    echo "Troubleshooting:"
    echo "  1. Check if cluster is running: docker ps | grep node"
    echo "  2. Check vLLM logs: docker exec \$(docker ps --format '{{.Names}}' | grep node | head -1) cat /tmp/vllm_serve.log | tail -30"
    echo "  3. Restart server: ./serve.sh"
    exit 1
fi
echo "Status: OK (HTTP 200)"
echo ""

# List models
echo "2. Available Models"
echo "-------------------"
curl -s "$BASE_URL/v1/models" | python3 -m json.tool 2>/dev/null || echo "Could not list models"
echo ""

# Completions test
echo "3. Completions API Test"
echo "-----------------------"
echo "Prompt: 'The capital of France is'"
RESPONSE=$(curl -s "$BASE_URL/v1/completions" \
    -H "Content-Type: application/json" \
    -d "{
        \"model\": \"$MODEL\",
        \"prompt\": \"The capital of France is\",
        \"max_tokens\": 32,
        \"temperature\": 0.1
    }")
echo "$RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$RESPONSE"
echo ""

# Chat completions test
echo "4. Chat Completions API Test"
echo "----------------------------"
echo "Message: 'Write a haiku about GPUs'"
RESPONSE=$(curl -s "$BASE_URL/v1/chat/completions" \
    -H "Content-Type: application/json" \
    -d "{
        \"model\": \"$MODEL\",
        \"messages\": [{\"role\": \"user\", \"content\": \"Write a haiku about GPUs\"}],
        \"max_tokens\": 64,
        \"temperature\": 0.7
    }")
echo "$RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$RESPONSE"
echo ""

# Performance test
echo "5. Simple Performance Test"
echo "--------------------------"
echo "Generating 100 tokens..."
START=$(date +%s.%N)
RESPONSE=$(curl -s "$BASE_URL/v1/completions" \
    -H "Content-Type: application/json" \
    -d "{
        \"model\": \"$MODEL\",
        \"prompt\": \"Explain the concept of distributed computing in detail:\",
        \"max_tokens\": 100,
        \"temperature\": 0.7
    }")
END=$(date +%s.%N)
DURATION=$(echo "$END - $START" | bc)
TOKENS=$(echo "$RESPONSE" | python3 -c "import sys,json; print(json.load(sys.stdin)['usage']['completion_tokens'])" 2>/dev/null || echo "?")
echo "Tokens generated: $TOKENS"
echo "Time: ${DURATION}s"
if [ "$TOKENS" != "?" ]; then
    TPS=$(echo "scale=2; $TOKENS / $DURATION" | bc)
    echo "Throughput: ${TPS} tokens/sec"
fi
echo ""

echo "=== All Tests Complete ==="
