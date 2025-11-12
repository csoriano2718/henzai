#!/bin/bash
echo "Testing streaming with reasoning parameter..."

curl -s http://localhost:8080/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "deepseek-r1",
    "messages": [
      {
        "role": "user",
        "content": "What is 7 * 8?"
      }
    ],
    "temperature": 0.6,
    "reasoning": true,
    "stream": true
  }' | head -30

echo ""
echo "=== Checking for reasoning_content in stream ==="
