#!/usr/bin/env bash
# create_endpoint.sh — Create a Nebius Serverless AI Endpoint
# Usage: ./scripts/create_endpoint.sh

set -euo pipefail

# ─── Load environment ────────────────────────────────────────────────────────
if [[ -f .env ]]; then
  set -a
  source .env
  set +a
fi

: "${NEBIUS_API_KEY:?NEBIUS_API_KEY is required}"
: "${NEBIUS_FOLDER_ID:?NEBIUS_FOLDER_ID is required}"

MODEL="${MODEL:-meta-llama/Meta-Llama-3.1-8B-Instruct-fast}"
ENDPOINT_NAME="${ENDPOINT_NAME:-nebiusbench-endpoint}"
MIN_REPLICAS="${MIN_REPLICAS:-1}"
MAX_REPLICAS="${MAX_REPLICAS:-5}"

NEBIUS_API_BASE="https://api.studio.nebius.com"

echo "=============================================="
echo " NebiusBench — Create Endpoint"
echo "=============================================="
echo "  Model:        ${MODEL}"
echo "  Name:         ${ENDPOINT_NAME}"
echo "  Min replicas: ${MIN_REPLICAS}"
echo "  Max replicas: ${MAX_REPLICAS}"
echo "  Folder ID:    ${NEBIUS_FOLDER_ID}"
echo ""

PAYLOAD=$(cat <<EOF
{
  "name": "${ENDPOINT_NAME}",
  "spec": {
    "model_uri": "gpt://${NEBIUS_FOLDER_ID}/${MODEL}",
    "scaling_policy": {
      "fixed": {
        "scale": ${MIN_REPLICAS}
      }
    }
  }
}
EOF
)

echo "Creating endpoint..."
RESPONSE=$(curl -s -X POST \
  "${NEBIUS_API_BASE}/ai/foundation-models/v1/inference/endpoints" \
  -H "Authorization: Bearer ${NEBIUS_API_KEY}" \
  -H "Content-Type: application/json" \
  -d "${PAYLOAD}")

echo ""
echo "Response:"
echo "${RESPONSE}" | python3 -m json.tool 2>/dev/null || echo "${RESPONSE}"

ENDPOINT_ID=$(echo "${RESPONSE}" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('id',''))" 2>/dev/null || true)

if [[ -n "${ENDPOINT_ID}" ]]; then
  echo ""
  echo "✓ Endpoint created: ${ENDPOINT_ID}"
  echo "  Set in your .env:"
  echo "  NEBIUS_ENDPOINT_ID=${ENDPOINT_ID}"
  echo "  NEBIUS_BASE_URL=${NEBIUS_API_BASE}/ai/foundation-models/v1/inference/endpoints/${ENDPOINT_ID}"
else
  echo ""
  echo "  Check the response above for endpoint ID."
fi
