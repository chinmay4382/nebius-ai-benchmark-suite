#!/usr/bin/env bash
# delete_job.sh — Cancel/delete a Nebius AI Job
# Usage: ./scripts/delete_job.sh [JOB_ID]

set -euo pipefail

if [[ -f .env ]]; then
  set -a
  source .env
  set +a
fi

: "${NEBIUS_API_KEY:?NEBIUS_API_KEY is required}"
: "${NEBIUS_FOLDER_ID:?NEBIUS_FOLDER_ID is required}"

JOB_ID="${1:-}"

if [[ -z "${JOB_ID}" ]]; then
  echo "ERROR: Provide JOB_ID as argument"
  echo "Usage: $0 <job-id>"
  exit 1
fi

NEBIUS_API_BASE="https://api.nebius.cloud/v1"

echo "Cancelling job ${JOB_ID}..."
RESPONSE=$(curl -s -X POST \
  "${NEBIUS_API_BASE}/folders/${NEBIUS_FOLDER_ID}/jobs/${JOB_ID}:cancel" \
  -H "Authorization: Bearer ${NEBIUS_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{}')

echo "Response:"
echo "${RESPONSE}" | python3 -m json.tool 2>/dev/null || echo "${RESPONSE}"
echo ""
echo "✓ Cancel request sent for job: ${JOB_ID}"
