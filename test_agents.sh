#!/bin/bash

BASE_URL="https://mylink-trn6.onrender.com"

echo "🧪 Testing SmartBot Autonomous Agents"
echo "===================================="

# 1. Check system status
echo ""
echo "1️⃣ Checking system status..."
curl -s "$BASE_URL/" | jq '.'

# 2. Check health
echo ""
echo "2️⃣ Checking health..."
curl -s "$BASE_URL/health" | jq '.'

# 3. Check agents status (before start)
echo ""
echo "3️⃣ Checking agents status (before start)..."
curl -s "$BASE_URL/autonomous-agents/metrics" | jq '.'

# 4. Start agents
echo ""
echo "4️⃣ Starting agents..."
curl -s -X POST "$BASE_URL/autonomous-agents/start" | jq '.'

# 5. Check agents status (after start)
echo ""
echo "5️⃣ Checking agents status (after start)..."
sleep 2
curl -s "$BASE_URL/autonomous-agents/health" | jq '.'

# 6. List all agents
echo ""
echo "6️⃣ Listing all agents..."
curl -s "$BASE_URL/autonomous-agents/agents" | jq '.'

# 7. Get detailed metrics
echo ""
echo "7️⃣ Getting detailed metrics..."
curl -s "$BASE_URL/autonomous-agents/metrics" | jq '.metrics.orchestrator'

echo ""
echo "✅ Testing complete!"

