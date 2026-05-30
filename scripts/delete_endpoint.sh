#!/usr/bin/env bash
# delete_endpoint.sh — Delete a Nebius Serverless AI Endpoint
# Usage: ./scripts/delete_endpoint.sh [ENDPOINT_ID]

set -euo pipefail

if [[ -f .env ]]; then
  set -a
  source .env
  set +a
fi

: "${NEBIUS_API_KEY:?NEBIUS_API_KEY is required}"

ENDPOINT_ID="${1:-${NEBIUS_ENDPOINT_ID:-}}"

if [[ -z "${ENDPOINT_ID}" ]]; then
  echo "ERROR: Provide ENDPOINT_ID as argument or set NEBIUS_ENDPOINT_ID in .env"
  echo "Usage: $0 <endpoint-id>"
  exit 1
fi

NEBIUS_API_BASE="https://api.studio.nebius.com"

echo "=============================================="
echo " NebiusBench — Delete Endpoint"
echo "=============================================="
echo "  Endpoint ID: ${ENDPOINT_ID}"
echo ""
echo "WARNING: This will permanently delete the endpoint."
read -r -p "Are you sure? [y/N] " confirm
if [[ "${confirm,,}" != "y" ]]; then
  echo "Aborted."
  exit 0
fi

echo "Deleting endpoint ${ENDPOINT_ID}..."
RESPONSE=$(curl -s -X DELETE \
  "${NEBIUS_API_BASE}/ai/foundation-models/v1/inference/endpoints/${ENDPOINT_ID}" \
  -H "Authorization: Bearer ${NEBIUS_API_KEY}")

echo "Response:"
echo "${RESPONSE}" | python3 -m json.tool 2>/dev/null || echo "${RESPONSE}"
echo ""
echo "✓ Delete request sent for endpoint: ${ENDPOINT_ID}"
