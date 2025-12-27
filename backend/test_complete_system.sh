#!/bin/bash

# Complete System Test - Tests ALL components end-to-end
# Tests: RAG, Auth, Sandbox, Agent, UI integration

set -e  # Exit on error

echo "🧪 COMPLETE SYSTEM TEST"
echo "======================="
echo ""

BASE_URL="http://localhost:8000"
WORKSPACE_ID="test_workspace_$(date +%s)"

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test counter
TESTS_PASSED=0
TESTS_FAILED=0

test_api() {
    local name="$1"
    local method="$2"
    local endpoint="$3"
    local data="$4"
    
    echo -n "Testing: $name... "
    
    if [ "$method" = "POST" ]; then
        response=$(curl -s -X POST "$BASE_URL$endpoint" \
            -H "Content-Type: application/json" \
            -d "$data" || echo "ERROR")
    else
        response=$(curl -s "$BASE_URL$endpoint" || echo "ERROR")
    fi
    
    if [[ "$response" == *"ERROR"* ]] || [[ "$response" == *"error"* ]]; then
        echo -e "${RED}✗ FAILED${NC}"
        echo "Response: $response"
        ((TESTS_FAILED++))
        return 1
    else
        echo -e "${GREEN}✓ PASSED${NC}"
        ((TESTS_PASSED++))
        return 0
    fi
}

# 1. Health Check
echo "1️⃣  Testing API Health"
echo "-------------------"
test_api "Health check" "GET" "/health" ""
echo ""

# 2. Workspace Creation
echo "2️⃣  Testing Workspace Creation"
echo "----------------------------"
test_api "Create workspace + sandbox" "POST" "/api/workspace/create-with-sandbox" \
    "{\"topic\":\"Test Project\",\"template\":\"python_dev\"}"
echo ""

# 3. Sandbox Operations
echo "3️⃣  Testing Sandbox"
echo "----------------"
test_api "Create sandbox" "POST" "/api/sandbox/create" \
    "{\"workspace_id\":\"$WORKSPACE_ID\",\"template\":\"python\"}"

test_api "Execute code" "POST" "/api/sandbox/workspace/$WORKSPACE_ID/execute" \
    "{\"code\":\"print('Hello from sandbox!')\",\"language\":\"python\"}"

test_api "List sandboxes" "GET" "/api/sandbox/list" ""
echo ""

# 4. Agent Tests
echo "4️⃣  Testing Autonomous Agent"
echo "--------------------------"
test_api "Agent solve (sync)" "POST" "/api/agent/solve-sync" \
    "{\"query\":\"Create a simple calculator function\",\"workspace_id\":\"$WORKSPACE_ID\"}"
echo ""

# 5. Authentication
echo "5️⃣  Testing Authentication"
echo "-----------------------"
test_api "User registration" "POST" "/api/auth/register" \
    "{\"email\":\"test@example.com\",\"password\":\"testpass123\",\"username\":\"testuser\"}"

test_api "User login" "POST" "/api/auth/login" \
    "{\"email\":\"test@example.com\",\"password\":\"testpass123\"}"
echo ""

# 6. RAG System (if vector service available)
echo "6️⃣  Testing RAG System"
echo "-------------------"
test_api "RAG search" "POST" "/api/rag/search" \
    "{\"query\":\"test\",\"workspace_id\":\"$WORKSPACE_ID\"}"
echo ""

# Summary
echo ""
echo "=============================="
echo "TEST SUMMARY"
echo "=============================="
echo -e "Tests Passed: ${GREEN}$TESTS_PASSED${NC}"
echo -e "Tests Failed: ${RED}$TESTS_FAILED${NC}"
echo ""

if [ $TESTS_FAILED -eq 0 ]; then
    echo -e "${GREEN}✅ ALL TESTS PASSED!${NC}"
    echo ""
    echo "🚀 System is ready for production!"
    exit 0
else
    echo -e "${RED}❌ SOME TESTS FAILED${NC}"
    echo ""
    echo "Check the errors above and fix them."
    exit 1
fi
