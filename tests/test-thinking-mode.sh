#!/bin/bash
echo "Testing DeepSeek-R1:14b with --thinking true..."

curl -s http://localhost:8080/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "deepseek-r1",
    "messages": [
      {
        "role": "user",
        "content": "What is 23 * 47? Show your reasoning."
      }
    ],
    "temperature": 0.6,
    "stream": false
  }' | jq -r '.choices[0].message.content' | tee /tmp/thinking-test.txt

echo ""
echo "=== CHECKING FOR TAGS ==="
if grep -q "<think>" /tmp/thinking-test.txt; then
    echo "✅✅✅ SUCCESS! <think> TAGS FOUND! ✅✅✅"
    echo ""
    echo "=== THINKING SECTION ==="
    sed -n '/<think>/,/<\/think>/p' /tmp/thinking-test.txt | head -50
elif grep -q "<reasoning>" /tmp/thinking-test.txt; then
    echo "✅✅✅ SUCCESS! <reasoning> TAGS FOUND! ✅✅✅"
    echo ""
    sed -n '/<reasoning>/,/<\/reasoning>/p' /tmp/thinking-test.txt | head -50
else
    echo "❌ No tags found"
    echo ""
    echo "=== RESPONSE (first 800 chars) ==="
    head -c 800 /tmp/thinking-test.txt
fi
