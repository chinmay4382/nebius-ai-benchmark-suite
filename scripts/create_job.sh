#!/usr/bin/env bash
# create_job.sh — Create a Nebius AI Job for benchmarking
# Usage: ./scripts/create_job.sh

set -euo pipefail

if [[ -f .env ]]; then
  set -a
  source .env
  set +a
fi

: "${NEBIUS_API_KEY:?NEBIUS_API_KEY is required}"
: "${NEBIUS_PROJECT_ID:?NEBIUS_PROJECT_ID is required}"
: "${NEBIUS_FOLDER_ID:?NEBIUS_FOLDER_ID is required}"

JOB_NAME="${JOB_NAME:-nebiusbench-job-$(date +%s)}"
JOB_IMAGE="${JOB_IMAGE:-cr.nebius.cloud/nebius/python:3.12-slim}"
JOB_COMMAND="${JOB_COMMAND:-python -c \"import time; print('NebiusBench probe'); time.sleep(5); print('Done')\"}"
RESOURCE_PRESET="${RESOURCE_PRESET:-2vcpu-8gb}"

NEBIUS_API_BASE="https://api.nebius.cloud/v1"

echo "=============================================="
echo " NebiusBench — Create AI Job"
echo "=============================================="
echo "  Job name:  ${JOB_NAME}"
echo "  Image:     ${JOB_IMAGE}"
echo "  Resources: ${RESOURCE_PRESET}"
echo "  Project:   ${NEBIUS_PROJECT_ID}"
echo ""

PAYLOAD=$(cat <<EOF
{
  "name": "${JOB_NAME}",
  "project_id": "${NEBIUS_PROJECT_ID}",
  "resources": {
    "platform": "cpu-d3",
    "preset": "${RESOURCE_PRESET}"
  },
  "container": {
    "image": "${JOB_IMAGE}",
    "command": ["bash", "-c", "${JOB_COMMAND}"],
    "env": [
      {"name": "NEBIUSBENCH_VERSION", "value": "0.1.0"}
    ]
  },
  "labels": {
    "created_by": "nebiusbench",
    "type": "benchmark"
  }
}
EOF
)

echo "Submitting job..."
RESPONSE=$(curl -s -X POST \
  "${NEBIUS_API_BASE}/folders/${NEBIUS_FOLDER_ID}/jobs" \
  -H "Authorization: Bearer ${NEBIUS_API_KEY}" \
  -H "Content-Type: application/json" \
  -d "${PAYLOAD}")

echo ""
echo "Response:"
echo "${RESPONSE}" | python3 -m json.tool 2>/dev/null || echo "${RESPONSE}"

JOB_ID=$(echo "${RESPONSE}" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('id',''))" 2>/dev/null || true)

if [[ -n "${JOB_ID}" ]]; then
  echo ""
  echo "✓ Job submitted: ${JOB_ID}"
  echo "  Monitor with: ./scripts/monitor_job.sh ${JOB_ID}"
else
  echo ""
  echo "  Check the response above for job details."
fi
