#!/bin/bash
# Test Qwen3-235B-A22B-AWQ server

PORT=${1:-8235}
MODEL="qwen3-235b-awq"
BASE_URL="http://localhost:$PORT"

echo "=== Testing Qwen3-235B-A22B-AWQ Server ==="
echo "URL: $BASE_URL"
echo ""

# Health check
echo "1. Health Check"
echo "----------------"
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "$BASE_URL/health" 2>/dev/null)
if [ "$HTTP_CODE" != "200" ]; then
    echo "ERROR: Server not responding (HTTP $HTTP_CODE)"
    echo ""
    echo "Troubleshooting:"
    echo "  1. Check if cluster is running: docker ps | grep node"
    echo "  2. Check vLLM logs: docker exec \$(docker ps --format '{{.Names}}' | grep node | head -1) cat /tmp/vllm_serve.log | tail -50"
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

# Chat completions test
echo "3. Chat Completions Test"
echo "------------------------"
echo "Message: 'Explain what makes MoE models efficient in one sentence.'"
RESPONSE=$(curl -s "$BASE_URL/v1/chat/completions" \
    -H "Content-Type: application/json" \
    -d "{
        \"model\": \"$MODEL\",
        \"messages\": [{\"role\": \"user\", \"content\": \"Explain what makes MoE models efficient in one sentence.\"}],
        \"max_tokens\": 128,
        \"temperature\": 0.7
    }")
echo "$RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$RESPONSE"
echo ""

# Performance test
echo "4. Performance Test (100 tokens)"
echo "---------------------------------"
START=$(date +%s.%N)
RESPONSE=$(curl -s "$BASE_URL/v1/chat/completions" \
    -H "Content-Type: application/json" \
    -d "{
        \"model\": \"$MODEL\",
        \"messages\": [{\"role\": \"user\", \"content\": \"Write a detailed explanation of distributed GPU inference.\"}],
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
