#!/bin/bash
echo "Testing DeepSeek-R1:14b reasoning output..."

curl -s http://localhost:8080/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "deepseek-r1",
    "messages": [
      {
        "role": "user",
        "content": "Please reason step by step, starting your response with <think> to show your detailed thought process. After your thinking section, provide your final answer. Question: A farmer has chickens and rabbits. In total there are 35 heads and 94 legs. How many chickens and how many rabbits?"
      }
    ],
    "temperature": 0.6,
    "stream": false
  }' | jq -r '.choices[0].message.content' | tee /tmp/deepseek14b-output.txt

echo ""
echo "=== CHECKING FOR REASONING TAGS ==="
if grep -q "<think>" /tmp/deepseek14b-output.txt; then
    echo "✅✅✅ <think> tag FOUND! ✅✅✅"
    echo ""
    echo "=== THINKING SECTION (first 800 chars) ==="
    sed -n '/<think>/,/<\/think>/p' /tmp/deepseek14b-output.txt | head -c 800
    echo ""
    echo "..."
elif grep -q "<reasoning>" /tmp/deepseek14b-output.txt; then
    echo "✅✅✅ <reasoning> tag FOUND! ✅✅✅"
    echo ""
    echo "=== REASONING SECTION (first 800 chars) ==="
    sed -n '/<reasoning>/,/<\/reasoning>/p' /tmp/deepseek14b-output.txt | head -c 800
    echo ""
    echo "..."
else
    echo "❌ No reasoning tags found"
    echo ""
    echo "=== FULL RESPONSE (first 1000 chars) ==="
    head -c 1000 /tmp/deepseek14b-output.txt
    echo ""
fi
