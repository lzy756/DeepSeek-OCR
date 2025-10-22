#!/bin/bash
# Test DeepSeek-OCR API with curl

API_BASE_URL="http://localhost:8000"
API_KEY="YOUR_API_KEY_HERE"  # Replace with your actual API key

echo "========================================"
echo "DeepSeek-OCR API Test Script"
echo "========================================"

# Test 1: Health check (no authentication required)
echo ""
echo "Test 1: Health Check"
echo "--------------------"
curl -X GET "$API_BASE_URL/health" | jq

# Test 2: Model info (requires authentication)
echo ""
echo "Test 2: Model Info"
echo "------------------"
curl -X GET "$API_BASE_URL/api/v1/info" \
  -H "X-API-Key: $API_KEY" | jq

# Test 3: OCR image file (multipart upload)
echo ""
echo "Test 3: OCR Image File"
echo "----------------------"
echo "Usage: Uncomment and provide image path"
# curl -X POST "$API_BASE_URL/api/v1/ocr/image" \
#   -H "X-API-Key: $API_KEY" \
#   -F "file=@/path/to/image.jpg" \
#   -F "mode=document_markdown" \
#   -F "resolution_preset=Gundam" \
#   -o result_image.zip
# echo "Result saved to: result_image.zip"

# Test 4: OCR image from URL
echo ""
echo "Test 4: OCR Image from URL"
echo "--------------------------"
echo "Usage: Uncomment and provide image URL"
# curl -X POST "$API_BASE_URL/api/v1/ocr/image" \
#   -H "X-API-Key: $API_KEY" \
#   -F "image_url=https://example.com/image.jpg" \
#   -F "mode=free_ocr" \
#   -o result_url.zip

# Test 5: OCR PDF synchronously
echo ""
echo "Test 5: OCR PDF (Sync)"
echo "---------------------"
echo "Usage: Uncomment and provide PDF path"
# curl -X POST "$API_BASE_URL/api/v1/ocr/pdf" \
#   -H "X-API-Key: $API_KEY" \
#   -F "file=@/path/to/document.pdf" \
#   -F "mode=document_markdown" \
#   -F "resolution_preset=Base" \
#   -o result_pdf.zip

# Test 6: OCR PDF asynchronously
echo ""
echo "Test 6: OCR PDF (Async)"
echo "-----------------------"
echo "Usage: Uncomment and provide PDF path"
# # Submit task
# TASK_RESPONSE=$(curl -s -X POST "$API_BASE_URL/api/v1/ocr/pdf/async" \
#   -H "X-API-Key: $API_KEY" \
#   -F "file=@/path/to/document.pdf" \
#   -F "mode=document_markdown")
# 
# TASK_ID=$(echo $TASK_RESPONSE | jq -r '.task_id')
# echo "Task ID: $TASK_ID"
# 
# # Check status
# echo "Checking status..."
# while true; do
#   STATUS_RESPONSE=$(curl -s -X GET "$API_BASE_URL/api/v1/ocr/task/$TASK_ID" \
#     -H "X-API-Key: $API_KEY")
#   
#   STATUS=$(echo $STATUS_RESPONSE | jq -r '.status')
#   echo "Status: $STATUS"
#   
#   if [ "$STATUS" = "completed" ]; then
#     echo "Task completed! Downloading result..."
#     curl -X GET "$API_BASE_URL/api/v1/ocr/task/$TASK_ID/download" \
#       -H "X-API-Key: $API_KEY" \
#       -o result_async.zip
#     echo "Result saved to: result_async.zip"
#     break
#   elif [ "$STATUS" = "failed" ]; then
#     echo "Task failed:"
#     echo $STATUS_RESPONSE | jq '.error'
#     break
#   fi
#   
#   sleep 2
# done

# Test 7: Test authentication (should fail without API key)
echo ""
echo "Test 7: Authentication Test (No API Key)"
echo "----------------------------------------"
curl -X GET "$API_BASE_URL/api/v1/info" | jq

echo ""
echo "========================================"
echo "Tests completed!"
echo "========================================"
echo "Note: Uncomment examples above and provide file paths to test OCR endpoints"
