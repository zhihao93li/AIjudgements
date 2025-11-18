#!/bin/bash
# API 测试脚本

echo "=============================="
echo "AI Judge System - API 测试"
echo "=============================="

API_BASE="http://localhost:8000/api"

echo ""
echo "1. 健康检查..."
curl -s "${API_BASE}/health" | jq .

echo ""
echo "2. 提交评分请求..."
curl -X POST "${API_BASE}/judge_entry" \
  -H "Content-Type: application/json" \
  -d '{
    "entry_id": "test_001",
    "image_url": "https://picsum.photos/800/600",
    "competition_type": "outfit",
    "extra_text": "测试穿搭图片"
  }' | jq .

echo ""
echo "3. 查询评分结果..."
sleep 2
curl -s "${API_BASE}/judge_entry/test_001" | jq .

echo ""
echo "测试完成！"

