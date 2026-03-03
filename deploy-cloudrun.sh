#!/bin/bash
# Deploy AAIF MCP Server to Google Cloud Run
#
# Prerequisites:
#   1. gcloud CLI installed: https://cloud.google.com/sdk/docs/install
#   2. Authenticated: gcloud auth login
#   3. Project set: gcloud config set project YOUR_PROJECT_ID
#
# Usage:
#   chmod +x deploy-cloudrun.sh
#   ./deploy-cloudrun.sh
#
# This builds the Docker image in Cloud Build and deploys to Cloud Run.
# No local Docker needed.

set -euo pipefail

# ── Configuration ──────────────────────────────────────────
SERVICE_NAME="${AAIF_SERVICE_NAME:-aaif-mcp-server}"
REGION="${AAIF_REGION:-us-central1}"
PROJECT_ID="${AAIF_PROJECT_ID:-$(gcloud config get-value project 2>/dev/null)}"

if [ -z "$PROJECT_ID" ]; then
  echo "❌ No GCP project set. Run: gcloud config set project YOUR_PROJECT_ID"
  exit 1
fi

IMAGE="gcr.io/${PROJECT_ID}/${SERVICE_NAME}"

echo "╔══════════════════════════════════════════════════════════╗"
echo "║  AAIF MCP Server → Google Cloud Run                     ║"
echo "╠══════════════════════════════════════════════════════════╣"
echo "║  Project:  ${PROJECT_ID}"
echo "║  Service:  ${SERVICE_NAME}"
echo "║  Region:   ${REGION}"
echo "║  Image:    ${IMAGE}"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""

# ── Step 1: Enable required APIs ──────────────────────────
echo "📦 Enabling Cloud Run and Container Registry APIs..."
gcloud services enable run.googleapis.com containerregistry.googleapis.com cloudbuild.googleapis.com --quiet

# ── Step 2: Build with Cloud Build (no local Docker needed) ──
echo "🔨 Building container image with Cloud Build..."
gcloud builds submit --tag "${IMAGE}" --quiet .

# ── Step 3: Deploy to Cloud Run ───────────────────────────
echo "🚀 Deploying to Cloud Run..."
gcloud run deploy "${SERVICE_NAME}" \
  --image "${IMAGE}" \
  --region "${REGION}" \
  --platform managed \
  --port 8080 \
  --allow-unauthenticated \
  --memory 512Mi \
  --cpu 1 \
  --min-instances 0 \
  --max-instances 3 \
  --timeout 300 \
  --set-env-vars "AAIF_MCP_TRANSPORT=streamable-http,FASTMCP_HOST=0.0.0.0,FASTMCP_PORT=8080,PIS_PROJECT_ID=lfZA9uadMdkwBqqHsj" \
  --quiet

# ── Step 4: Get the URL ───────────────────────────────────
URL=$(gcloud run services describe "${SERVICE_NAME}" --region "${REGION}" --format 'value(status.url)')

echo ""
echo "╔══════════════════════════════════════════════════════════╗"
echo "║  ✅ DEPLOYED SUCCESSFULLY                               ║"
echo "╠══════════════════════════════════════════════════════════╣"
echo "║  URL: ${URL}"
echo "║  MCP Endpoint: ${URL}/mcp"
echo "╠══════════════════════════════════════════════════════════╣"
echo "║  Claude Desktop config:                                  ║"
echo "║  {                                                       ║"
echo "║    \"mcpServers\": {                                      ║"
echo "║      \"aaif-onboarding\": {                               ║"
echo "║        \"type\": \"http\",                                  ║"
echo "║        \"url\": \"${URL}/mcp\"                     ║"
echo "║      }                                                   ║"
echo "║    }                                                     ║"
echo "║  }                                                       ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""
echo "Test it: curl ${URL}/mcp -X POST -H 'Content-Type: application/json' -d '{\"jsonrpc\":\"2.0\",\"method\":\"initialize\",\"id\":1,\"params\":{\"protocolVersion\":\"2024-11-05\",\"capabilities\":{},\"clientInfo\":{\"name\":\"test\",\"version\":\"0.1\"}}}'"
