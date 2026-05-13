#!/bin/bash
# =============================================================================
# Déploiement rapide Mina sur Cloud Run
# Projet: bodycoachocr
# =============================================================================

set -e

PROJECT_ID="bodycoachocr"
REGION="europe-west1"
SERVICE_NAME="mina-indexer"

echo "🚀 DÉPLOIEMENT MINA - $PROJECT_ID"

# 1. Configuration projet
gcloud config set project $PROJECT_ID

# 2. Activer les APIs
gcloud services enable \
    run.googleapis.com \
    cloudbuild.googleapis.com \
    secretmanager.googleapis.com \
    aiplatform.googleapis.com \
    storage.googleapis.com

# 3. Créer les secrets (si pas déjà fait)
echo "📝 Configuration des secrets..."

# Qdrant URL
echo -n "https://729d910f-a0c0-43e0-8441-8afb3fcf5ec1.europe-west3-0.gcp.cloud.qdrant.io:6333" | \
    gcloud secrets create QDRANT_URL --data-file=- 2>/dev/null || \
    echo "Secret QDRANT_URL existe déjà"

# Qdrant API Key
echo -n "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJhY2Nlc3MiOiJtIn0.VS3rmVsSl0QhByrItM5-qYNpozlJyNXX1mL0qjvUilI" | \
    gcloud secrets create QDRANT_API_KEY --data-file=- 2>/dev/null || \
    echo "Secret QDRANT_API_KEY existe déjà"

# 4. Build et déploiement via Cloud Build
echo "🏗️ Build et déploiement..."
gcloud builds submit --config cloudbuild.yaml

echo "✅ Déploiement terminé!"
echo ""
echo "Pour lancer l'indexation:"
echo "  gcloud run jobs execute mina-indexer --region=$REGION"
