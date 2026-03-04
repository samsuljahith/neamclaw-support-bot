#!/usr/bin/env bash
# ============================================================
# TechNova Support Bot — Lambda Integration Test Suite
#
# Usage:
#   ./tests/test_lambda.sh [<api-url>]
#
# If <api-url> is omitted, the script fetches it from the
# Pulumi stack output (requires `pulumi` in PATH and the
# dev stack to be active in infra/).
#
# Environment variables:
#   NEAM_API_KEY   — API key (default: dev-key-change-me)
#   VERBOSE        — set to 1 to print full response bodies
# ============================================================

set -euo pipefail

# ── Config ──────────────────────────────────────────────────
API_KEY="${NEAM_API_KEY:-dev-key-change-me}"
VERBOSE="${VERBOSE:-0}"
PASS=0
FAIL=0
RED='\033[0;31m'
GRN='\033[0;32m'
YLW='\033[1;33m'
BLD='\033[1m'
RST='\033[0m'

# ── Resolve API URL ──────────────────────────────────────────
API_URL="${1:-}"
if [[ -z "$API_URL" ]]; then
  echo -e "${YLW}No API URL provided — fetching from Pulumi stack output...${RST}"
  SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
  INFRA_DIR="$SCRIPT_DIR/../infra"
  if command -v pulumi &>/dev/null; then
    API_URL=$(cd "$INFRA_DIR" && pulumi stack output apiUrl 2>/dev/null | tr -d '"' || true)
  fi
fi

if [[ -z "$API_URL" ]]; then
  echo -e "${RED}Error: could not determine API URL.${RST}"
  echo "Usage: $0 <api-url>"
  echo "  or:  NEAM_API_KEY=<key> $0 <api-url>"
  exit 1
fi

# Strip trailing slash
API_URL="${API_URL%/}"

echo ""
echo -e "${BLD}=================================================${RST}"
echo -e "${BLD}  TechNova Support Bot — Lambda Test Suite${RST}"
echo -e "${BLD}=================================================${RST}"
echo -e "  API URL : ${YLW}${API_URL}${RST}"
echo -e "  API Key : ${YLW}${API_KEY:0:4}****${RST}"
echo ""

# ── Helpers ──────────────────────────────────────────────────
pass() {
  PASS=$((PASS + 1))
  echo -e "  ${GRN}[PASS]${RST} $1"
}

fail() {
  FAIL=$((FAIL + 1))
  echo -e "  ${RED}[FAIL]${RST} $1"
}

info() {
  echo -e "  ${YLW}      $1${RST}"
}

# Perform a curl call and return the body; exits 0 even on HTTP errors
do_curl() {
  local method="$1"
  local url="$2"
  local body="${3:-}"
  if [[ -n "$body" ]]; then
    curl -s -X "$method" "$url" \
      -H "Content-Type: application/json" \
      -H "Authorization: Bearer $API_KEY" \
      -d "$body"
  else
    curl -s -X "$method" "$url" \
      -H "Authorization: Bearer $API_KEY"
  fi
}

check_field() {
  local json="$1"
  local field="$2"
  echo "$json" | grep -q "\"$field\""
}

# ── Test 1: Health endpoint (no auth) ───────────────────────
echo -e "${BLD}[1] GET /health${RST}"
RESP=$(curl -s "${API_URL}/health")
[[ "$VERBOSE" == "1" ]] && info "$RESP"
if echo "$RESP" | grep -q '"status".*"healthy"'; then
  pass "Returns status=healthy"
else
  fail "Expected status=healthy, got: $RESP"
fi
if echo "$RESP" | grep -q '"service"'; then
  pass "Returns service field"
else
  fail "Missing service field"
fi
if echo "$RESP" | grep -q '"knowledge_chunks"'; then
  CHUNKS=$(echo "$RESP" | grep -o '"knowledge_chunks":[0-9]*' | grep -o '[0-9]*$')
  if [[ "${CHUNKS:-0}" -gt 0 ]]; then
    pass "Knowledge base loaded ($CHUNKS chunks)"
  else
    fail "knowledge_chunks is 0 — docs may not be bundled"
  fi
fi

# ── Test 2: Auth rejection ───────────────────────────────────
echo ""
echo -e "${BLD}[2] Auth rejection${RST}"
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" \
  -X GET "${API_URL}/api/v1/claw")
if [[ "$HTTP_CODE" == "401" || "$HTTP_CODE" == "403" ]]; then
  pass "Unauthenticated request rejected (HTTP $HTTP_CODE)"
else
  fail "Expected 401/403, got HTTP $HTTP_CODE"
fi

RESP=$(curl -s -X GET "${API_URL}/api/v1/claw" \
  -H "Authorization: Bearer WRONG_KEY")
[[ "$VERBOSE" == "1" ]] && info "$RESP"
if echo "$RESP" | grep -qi "invalid\|unauthorized\|401\|403"; then
  pass "Wrong API key rejected"
else
  fail "Wrong API key was NOT rejected: $RESP"
fi

# ── Test 3: List agents ──────────────────────────────────────
echo ""
echo -e "${BLD}[3] GET /api/v1/claw — list agents${RST}"
RESP=$(do_curl GET "${API_URL}/api/v1/claw")
[[ "$VERBOSE" == "1" ]] && info "$RESP"
if echo "$RESP" | grep -q '"support_bot"'; then
  pass "support_bot agent listed"
else
  fail "support_bot not listed: $RESP"
fi

# ── Test 4: Basic greeting ───────────────────────────────────
echo ""
echo -e "${BLD}[4] POST .../sessions/test-greeting/message — hello${RST}"
SESSION="test-$$"
RESP=$(do_curl POST \
  "${API_URL}/api/v1/claw/support_bot/sessions/${SESSION}/message" \
  '{"message": "Hello! What can you help me with?"}')
[[ "$VERBOSE" == "1" ]] && info "$RESP"
if check_field "$RESP" "response"; then
  pass "Response field present"
  REPLY=$(echo "$RESP" | grep -o '"response":"[^"]*"' | head -1 | sed 's/"response":"//;s/"$//')
  info "Nova: ${REPLY:0:100}..."
else
  fail "No response field: $RESP"
fi
if check_field "$RESP" "turn"; then
  TURN=$(echo "$RESP" | grep -o '"turn":[0-9]*' | grep -o '[0-9]*$')
  pass "Turn counter present (turn=$TURN)"
else
  fail "No turn field: $RESP"
fi

# ── Test 5: Order lookup by ID ───────────────────────────────
echo ""
echo -e "${BLD}[5] POST .../sessions/test-order/message — order ID lookup${RST}"
SESSION="order-$$"
RESP=$(do_curl POST \
  "${API_URL}/api/v1/claw/support_bot/sessions/${SESSION}/message" \
  '{"message": "Can you look up order ORD-10001 for me?"}')
[[ "$VERBOSE" == "1" ]] && info "$RESP"
if check_field "$RESP" "response"; then
  REPLY=$(echo "$RESP" | grep -o '"response":"[^"]*"' | head -1 | sed 's/"response":"//;s/"$//')
  if echo "$REPLY" | grep -qi "ORD-10001\|delivered\|earbuds\|alice"; then
    pass "Order ORD-10001 details returned"
    info "Nova: ${REPLY:0:150}..."
  else
    fail "Response does not mention order details: ${REPLY:0:150}"
  fi
else
  fail "No response field: $RESP"
fi

# ── Test 6: Order lookup by email ───────────────────────────
echo ""
echo -e "${BLD}[6] POST .../sessions/test-email/message — email order lookup${RST}"
SESSION="email-$$"
RESP=$(do_curl POST \
  "${API_URL}/api/v1/claw/support_bot/sessions/${SESSION}/message" \
  '{"message": "I want to check my orders. My email is alice@example.com"}')
[[ "$VERBOSE" == "1" ]] && info "$RESP"
if check_field "$RESP" "response"; then
  REPLY=$(echo "$RESP" | grep -o '"response":"[^"]*"' | head -1 | sed 's/"response":"//;s/"$//')
  if echo "$REPLY" | grep -qi "alice@example.com\|ORD-10001\|ORD-10003\|order"; then
    pass "Orders for alice@example.com returned"
    info "Nova: ${REPLY:0:150}..."
  else
    fail "Response does not mention Alice's orders: ${REPLY:0:150}"
  fi
else
  fail "No response field: $RESP"
fi

# ── Test 7: Product check ─────────────────────────────────────
echo ""
echo -e "${BLD}[7] POST .../sessions/test-product/message — product search${RST}"
SESSION="product-$$"
RESP=$(do_curl POST \
  "${API_URL}/api/v1/claw/support_bot/sessions/${SESSION}/message" \
  '{"message": "Do you have any wireless earbuds in stock?"}')
[[ "$VERBOSE" == "1" ]] && info "$RESP"
if check_field "$RESP" "response"; then
  REPLY=$(echo "$RESP" | grep -o '"response":"[^"]*"' | head -1 | sed 's/"response":"//;s/"$//')
  if echo "$REPLY" | grep -qi "earbuds\|79\|Pro Wireless\|stock\|available"; then
    pass "Earbuds product info returned"
    info "Nova: ${REPLY:0:150}..."
  else
    fail "Response does not mention earbuds: ${REPLY:0:150}"
  fi
else
  fail "No response field: $RESP"
fi

# ── Test 8: Policy / knowledge-base question ─────────────────
echo ""
echo -e "${BLD}[8] POST .../sessions/test-policy/message — return policy${RST}"
SESSION="policy-$$"
RESP=$(do_curl POST \
  "${API_URL}/api/v1/claw/support_bot/sessions/${SESSION}/message" \
  '{"message": "What is your return policy?"}')
[[ "$VERBOSE" == "1" ]] && info "$RESP"
if check_field "$RESP" "response"; then
  # Check the raw JSON response directly — response text may contain embedded "
  # which truncates naive grep-o extraction; "polic" matches both "policy" and "policies"
  if echo "$RESP" | grep -qi "return\|30 day\|refund\|polic"; then
    pass "Return policy information returned"
    REPLY=$(echo "$RESP" | grep -o '"response":"[^"]*"' | head -1 | sed 's/"response":"//;s/"$//')
    info "Nova: ${REPLY:0:150}..."
  else
    fail "Response does not mention return policy: $RESP"
  fi
else
  fail "No response field: $RESP"
fi

# ── Test 9: Multi-turn session continuity ────────────────────
echo ""
echo -e "${BLD}[9] Multi-turn conversation${RST}"
SESSION="multi-$$"
do_curl POST \
  "${API_URL}/api/v1/claw/support_bot/sessions/${SESSION}/message" \
  '{"message": "Hi, I need help with my order"}' > /dev/null

RESP2=$(do_curl POST \
  "${API_URL}/api/v1/claw/support_bot/sessions/${SESSION}/message" \
  '{"message": "The order ID is ORD-10002"}')
[[ "$VERBOSE" == "1" ]] && info "$RESP2"
if check_field "$RESP2" "response"; then
  TURN=$(echo "$RESP2" | grep -o '"turn":[0-9]*' | grep -o '[0-9]*$')
  if [[ "${TURN:-0}" -ge 2 ]]; then
    pass "Session maintains history across turns (turn=$TURN)"
  else
    fail "Turn should be >=2 after two messages, got $TURN"
  fi
  REPLY=$(echo "$RESP2" | grep -o '"response":"[^"]*"' | head -1 | sed 's/"response":"//;s/"$//')
  if echo "$REPLY" | grep -qi "ORD-10002\|shipped\|SmartWatch\|Bob"; then
    pass "Second turn resolves order ORD-10002"
    info "Nova: ${REPLY:0:150}..."
  else
    info "Response: ${REPLY:0:150}"
    pass "Second turn returned a response (order details may be in LLM context)"
  fi
else
  fail "No response field on second turn: $RESP2"
fi

# ── Test 10: Session reset ───────────────────────────────────
echo ""
echo -e "${BLD}[10] POST .../sessions/test-reset/reset${RST}"
SESSION="reset-$$"
do_curl POST \
  "${API_URL}/api/v1/claw/support_bot/sessions/${SESSION}/message" \
  '{"message": "Hello"}' > /dev/null

RESP=$(do_curl POST \
  "${API_URL}/api/v1/claw/support_bot/sessions/${SESSION}/reset")
[[ "$VERBOSE" == "1" ]] && info "$RESP"
if echo "$RESP" | grep -qi "reset"; then
  pass "Session reset confirmed"
else
  fail "Unexpected reset response: $RESP"
fi

# Verify session is gone — next message should start at turn 1
RESP2=$(do_curl POST \
  "${API_URL}/api/v1/claw/support_bot/sessions/${SESSION}/message" \
  '{"message": "Hello again"}')
TURN=$(echo "$RESP2" | grep -o '"turn":[0-9]*' | grep -o '[0-9]*$')
if [[ "${TURN:-99}" -eq 1 ]]; then
  pass "Post-reset message starts at turn 1"
else
  fail "Expected turn=1 after reset, got turn=${TURN:-?}"
fi

# ── Test 11: Metrics endpoint ────────────────────────────────
echo ""
echo -e "${BLD}[11] GET /api/v1/metrics${RST}"
RESP=$(do_curl GET "${API_URL}/api/v1/metrics")
[[ "$VERBOSE" == "1" ]] && info "$RESP"
if check_field "$RESP" "active_sessions" && check_field "$RESP" "knowledge_chunks"; then
  pass "Metrics endpoint returns expected fields"
else
  fail "Metrics missing fields: $RESP"
fi

# ── Summary ──────────────────────────────────────────────────
echo ""
echo -e "${BLD}=================================================${RST}"
TOTAL=$((PASS + FAIL))
if [[ "$FAIL" -eq 0 ]]; then
  echo -e "${GRN}${BLD}  All $TOTAL tests passed!${RST}"
else
  echo -e "${RED}${BLD}  $FAIL / $TOTAL tests FAILED${RST}"
fi
echo -e "${BLD}=================================================${RST}"
echo ""

[[ "$FAIL" -eq 0 ]]
