#!/bin/bash
echo "Testing DeepSeek-R1 with a complex reasoning question..."

curl -s http://localhost:8080/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "deepseek-r1",
    "messages": [
      {
        "role": "user",
        "content": "A farmer has chickens and rabbits. In total there are 35 heads and 94 legs. How many chickens and how many rabbits does the farmer have? Show your step-by-step reasoning."
      }
    ],
    "temperature": 0.6,
    "stream": false
  }' | jq -r '.choices[0].message.content' | tee /tmp/complex-output.txt

echo ""
echo "=== CHECKING FOR TAGS ==="
if grep -q "<think>" /tmp/complex-output.txt; then
    echo "✅ <think> tag FOUND!"
    echo ""
    echo "=== REASONING SECTION ==="
    sed -n '/<think>/,/<\/think>/p' /tmp/complex-output.txt | head -50
else
    echo "❌ No <think> tag"
    echo ""
    echo "=== FIRST 800 CHARS ==="
    head -c 800 /tmp/complex-output.txt
fi
