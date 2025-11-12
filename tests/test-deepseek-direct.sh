#!/bin/bash
echo "Testing DeepSeek-R1 with explicit <think> instruction..."

curl -s http://localhost:8080/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "deepseek-r1",
    "messages": [
      {
        "role": "user",
        "content": "Please start your response with <think> and show your reasoning. Then provide the answer. Question: What is 25 * 37?"
      }
    ],
    "temperature": 0.6,
    "stream": false
  }' | jq -r '.choices[0].message.content' | tee /tmp/deepseek-output.txt

echo ""
echo "=== CHECKING OUTPUT ==="
if grep -q "<think>" /tmp/deepseek-output.txt; then
    echo "✅ <think> tag found!"
else
    echo "❌ No <think> tag"
fi

echo ""
echo "=== FIRST 500 CHARS ==="
head -c 500 /tmp/deepseek-output.txt
