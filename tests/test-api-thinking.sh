#!/bin/bash
echo "Testing with 'reasoning' parameter in API call..."

curl -s http://localhost:8080/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "deepseek-r1",
    "messages": [
      {
        "role": "user",
        "content": "What is 19 * 23?"
      }
    ],
    "temperature": 0.6,
    "reasoning": true,
    "stream": false
  }' | jq '.' | tee /tmp/api-reasoning-test.json

echo ""
echo "=== CHECKING RESPONSE ==="
jq -r '.choices[0].message.content' /tmp/api-reasoning-test.json | head -c 500
