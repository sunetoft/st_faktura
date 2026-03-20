#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVICE_NAME="${SERVICE_NAME:-st-faktura}"
REGION="${REGION:-europe-north1}"
PROJECT_ID="${PROJECT_ID:-$(gcloud config get-value project 2>/dev/null || true)}"

if [[ -z "${PROJECT_ID}" ]]; then
  echo "Error: PROJECT_ID is not set and no gcloud project is configured." >&2
  echo "Set PROJECT_ID or run: gcloud config set project <project-id>" >&2
  exit 1
fi

if [[ ! -f "${ROOT_DIR}/Dockerfile" ]]; then
  echo "Error: Dockerfile not found in ${ROOT_DIR}." >&2
  exit 1
fi

IMAGE="gcr.io/${PROJECT_ID}/${SERVICE_NAME}:latest"

echo "Deploying ${SERVICE_NAME} to ${PROJECT_ID} (${REGION})"

echo "- Building image ${IMAGE}"
gcloud builds submit "${ROOT_DIR}" --tag "${IMAGE}" --project "${PROJECT_ID}"

echo "- Deploying to Cloud Run"
gcloud run deploy "${SERVICE_NAME}" \
  --region "${REGION}" \
  --platform managed \
  --image "${IMAGE}" \
  --project "${PROJECT_ID}"

URL="$(gcloud run services describe "${SERVICE_NAME}" --region "${REGION}" --project "${PROJECT_ID}" --format='value(status.url)')"

echo "- Done. Service URL: ${URL}"
