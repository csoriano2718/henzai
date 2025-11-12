#!/bin/bash
echo "Testing Qwen QwQ reasoning output..."

curl -s http://localhost:8080/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "qwq",
    "messages": [
      {
        "role": "user",
        "content": "What is 17 * 23? Show your reasoning."
      }
    ],
    "temperature": 0.6,
    "stream": false
  }' | jq -r '.choices[0].message.content' | tee /tmp/qwq-output.txt

echo ""
echo "=== CHECKING FOR REASONING TAGS ==="
if grep -q "<think>" /tmp/qwq-output.txt; then
    echo "✅ <think> tag FOUND!"
    echo ""
    echo "=== REASONING SECTION ==="
    sed -n '/<think>/,/<\/think>/p' /tmp/qwq-output.txt | head -100
elif grep -q "<reasoning>" /tmp/qwq-output.txt; then
    echo "✅ <reasoning> tag FOUND!"
    echo ""
    echo "=== REASONING SECTION ==="
    sed -n '/<reasoning>/,/<\/reasoning>/p' /tmp/qwq-output.txt | head -100
else
    echo "❌ No reasoning tags found"
    echo ""
    echo "=== FIRST 1000 CHARS ==="
    head -c 1000 /tmp/qwq-output.txt
fi
