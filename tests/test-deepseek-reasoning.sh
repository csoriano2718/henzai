#!/bin/bash
# Test what DeepSeek-R1 actually outputs

echo "Testing DeepSeek-R1 reasoning output..."
echo ""

response=$(curl -s http://localhost:8080/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "messages":[
      {"role":"system","content":"When answering questions, show your step-by-step thinking process using <think> tags before your final answer."},
      {"role":"user","content":"How many letter r are in the word strawberry?"}
    ],
    "stream":false,
    "max_tokens":500
  }' | jq -r '.choices[0].message.content')

echo "=== RAW RESPONSE ==="
echo "$response"
echo ""
echo "=== CHECKING FOR TAGS ==="
if echo "$response" | grep -q "<think>"; then
  echo "✅ Found <think> tag!"
else
  echo "❌ No <think> tag found"
fi

if echo "$response" | grep -q "<reasoning>"; then
  echo "✅ Found <reasoning> tag!"
else
  echo "❌ No <reasoning> tag found"
fi

