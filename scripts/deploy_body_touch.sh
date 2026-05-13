#!/bin/bash
# =============================================================================
# Déploiement Mina Body Touch (Streamlit) sur Cloud Run
# =============================================================================

set -e

# Configuration
PROJECT_ID="${GCP_PROJECT_ID:-bodycoachocr}"
REGION="${GCP_REGION:-europe-west1}"
SERVICE_NAME="mina-body-touch"
IMAGE_NAME="gcr.io/${PROJECT_ID}/${SERVICE_NAME}"

# Couleurs
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}"
echo "=============================================="
echo " 🚀 DÉPLOIEMENT MINA BODY TOUCH - PILOTE"
echo "=============================================="
echo -e "${NC}"

# Vérifications
echo "📋 Vérification prérequis..."
if ! command -v gcloud &> /dev/null; then
    echo "❌ gcloud CLI non installé"
    exit 1
fi

if ! command -v docker &> /dev/null; then
    echo "❌ Docker non installé"
    exit 1
fi

# Configuration gcloud
echo "🔧 Configuration GCP..."
gcloud config set project $PROJECT_ID
gcloud config set run/region $REGION

# Activer APIs
echo "🔌 Activation APIs..."
gcloud services enable \
    run.googleapis.com \
    cloudbuild.googleapis.com \
    containerregistry.googleapis.com \
    speech.googleapis.com \
    texttospeech.googleapis.com \
    aiplatform.googleapis.com \
    --quiet

# Build avec Dockerfile.streamlit
echo "🏗️  Build image Docker..."
docker build -f Dockerfile.streamlit -t $IMAGE_NAME:latest .

# Push
echo "📤 Push vers Container Registry..."
gcloud auth configure-docker --quiet
docker push $IMAGE_NAME:latest

# Déploiement
echo "☁️  Déploiement Cloud Run..."
gcloud run deploy $SERVICE_NAME \
    --image $IMAGE_NAME:latest \
    --platform managed \
    --region $REGION \
    --memory 1Gi \
    --cpu 1 \
    --timeout 300 \
    --concurrency 80 \
    --min-instances 0 \
    --max-instances 3 \
    --set-env-vars "QDRANT_URL=${QDRANT_URL}" \
    --set-env-vars "QDRANT_API_KEY=${QDRANT_API_KEY}" \
    --set-env-vars "GOOGLE_API_KEY=${GOOGLE_API_KEY}" \
    --set-env-vars "GCS_PROJECT_ID=${PROJECT_ID}" \
    --set-env-vars "VERTEX_AI_LOCATION=${REGION}" \
    --allow-unauthenticated \
    --quiet

# Récupérer l'URL
SERVICE_URL=$(gcloud run services describe $SERVICE_NAME --region=$REGION --format='value(status.url)')

echo ""
echo -e "${GREEN}=============================================="
echo " ✅ DÉPLOIEMENT RÉUSSI !"
echo "=============================================="
echo -e "${NC}"
echo ""
echo "🔗 URL du service:"
echo "   $SERVICE_URL"
echo ""
echo "📱 Scanne ce lien sur mobile pour tester Mina !"
echo ""
