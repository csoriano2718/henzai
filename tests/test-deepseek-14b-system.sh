#!/bin/bash
echo "Testing DeepSeek-R1:14b with system prompt..."

curl -s http://localhost:8080/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "deepseek-r1",
    "messages": [
      {
        "role": "system",
        "content": "You are a reasoning AI. Always start your response with <think> tag, show your detailed reasoning process inside the tags, then close with </think> and provide your final answer."
      },
      {
        "role": "user",
        "content": "What is 47 * 89?"
      }
    ],
    "temperature": 0.6,
    "stream": false
  }' | jq -r '.choices[0].message.content' | tee /tmp/deepseek14b-system.txt

echo ""
if grep -q "<think>" /tmp/deepseek14b-system.txt; then
    echo "✅✅✅ SUCCESS! <think> tags found! ✅✅✅"
else
    echo "❌ Still no <think> tags"
    echo ""
    head -c 500 /tmp/deepseek14b-system.txt
fi
