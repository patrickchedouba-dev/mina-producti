#!/bin/bash
# Script de déploiement et exécution du test qualité Qdrant sur Cloud Run

set -e

PROJECT_ID="${PROJECT_ID:-bodycoachocr}"
REGION="${REGION:-europe-west1}"
SERVICE_NAME="qdrant-quality-test"
IMAGE_NAME="gcr.io/${PROJECT_ID}/${SERVICE_NAME}"

echo "=================================================="
echo "🚀 DÉPLOIEMENT TEST QUALITÉ QDRANT"
echo "=================================================="
echo "Project: ${PROJECT_ID}"
echo "Region: ${REGION}"
echo "Image: ${IMAGE_NAME}"
echo ""

# 1. Build de l'image Docker
echo "📦 Build de l'image Docker..."
docker build -f Dockerfile.test -t ${IMAGE_NAME} .

# 2. Push vers Container Registry
echo ""
echo "⬆️ Push vers GCR..."
docker push ${IMAGE_NAME}

# 3. Déploiement sur Cloud Run (en mode job pour une exécution unique)
echo ""
echo "🌐 Déploiement sur Cloud Run..."

# Vérifier si le job existe déjà
if gcloud run jobs describe ${SERVICE_NAME} --region=${REGION} --project=${PROJECT_ID} --quiet 2>/dev/null; then
    echo "   Job existant, mise à jour..."
    gcloud run jobs update ${SERVICE_NAME} \
        --image=${IMAGE_NAME} \
        --region=${REGION} \
        --project=${PROJECT_ID} \
        --set-secrets="QDRANT_URL=QDRANT_URL:latest,QDRANT_API_KEY=QDRANT_API_KEY:latest" \
        --memory=512Mi \
        --cpu=1 \
        --max-retries=0 \
        --task-timeout=300s
else
    echo "   Création du nouveau job..."
    gcloud run jobs create ${SERVICE_NAME} \
        --image=${IMAGE_NAME} \
        --region=${REGION} \
        --project=${PROJECT_ID} \
        --set-secrets="QDRANT_URL=QDRANT_URL:latest,QDRANT_API_KEY=QDRANT_API_KEY:latest" \
        --memory=512Mi \
        --cpu=1 \
        --max-retries=0 \
        --task-timeout=300s
fi

# 4. Exécution du job
echo ""
echo "▶️ Exécution du test..."
EXECUTION_ID=$(gcloud run jobs execute ${SERVICE_NAME} \
    --region=${REGION} \
    --project=${PROJECT_ID} \
    --format="value(metadata.name)" \
    --wait)

# 5. Récupération des logs
echo ""
echo "📋 Récupération des résultats..."
echo ""
echo "=================================================="
echo "📊 RÉSULTATS DU TEST QUALITÉ"
echo "=================================================="

gcloud logging read "resource.type=cloud_run_job AND resource.labels.job_name=${SERVICE_NAME}" \
    --project=${PROJECT_ID} \
    --limit=200 \
    --format="value(textPayload)" \
    | tac

echo ""
echo "=================================================="
echo "✅ Test terminé!"
echo "=================================================="
