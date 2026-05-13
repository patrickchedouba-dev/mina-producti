#!/bin/bash
# =============================================================================
# Script de déploiement Mina sur Google Cloud Run
# =============================================================================

set -e  # Arrêt en cas d'erreur

# Configuration
PROJECT_ID="${GCP_PROJECT_ID:-}"
REGION="${GCP_REGION:-europe-west1}"
SERVICE_NAME="${CLOUD_RUN_SERVICE:-mina-indexer}"
IMAGE_NAME="gcr.io/${PROJECT_ID}/${SERVICE_NAME}"

# Couleurs pour le terminal
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}"
echo "=============================================="
echo " 🚀 DÉPLOIEMENT MINA - CLOUD RUN"
echo "=============================================="
echo -e "${NC}"

# Vérification des prérequis
check_prerequisites() {
    echo "📋 Vérification des prérequis..."
    
    # Vérifier gcloud
    if ! command -v gcloud &> /dev/null; then
        echo -e "${RED}❌ gcloud CLI non installé${NC}"
        echo "   Installer: https://cloud.google.com/sdk/docs/install"
        exit 1
    fi
    
    # Vérifier docker
    if ! command -v docker &> /dev/null; then
        echo -e "${RED}❌ Docker non installé${NC}"
        exit 1
    fi
    
    # Vérifier PROJECT_ID
    if [ -z "$PROJECT_ID" ]; then
        echo -e "${RED}❌ GCP_PROJECT_ID non défini${NC}"
        echo "   export GCP_PROJECT_ID=your-project-id"
        exit 1
    fi
    
    echo -e "${GREEN}✅ Prérequis OK${NC}"
}

# Configuration gcloud
setup_gcloud() {
    echo ""
    echo "🔧 Configuration gcloud..."
    
    gcloud config set project $PROJECT_ID
    gcloud config set run/region $REGION
    
    # Activer les APIs nécessaires
    echo "   Activation des APIs..."
    gcloud services enable \
        run.googleapis.com \
        cloudbuild.googleapis.com \
        containerregistry.googleapis.com \
        secretmanager.googleapis.com \
        aiplatform.googleapis.com \
        --quiet
    
    echo -e "${GREEN}✅ gcloud configuré${NC}"
}

# Configuration des secrets
setup_secrets() {
    echo ""
    echo "🔐 Configuration des secrets..."
    
    # Vérifier si les secrets existent, sinon les créer
    SECRETS=("QDRANT_URL" "QDRANT_API_KEY")
    
    for secret in "${SECRETS[@]}"; do
        if ! gcloud secrets describe $secret --project=$PROJECT_ID &> /dev/null; then
            echo -e "${YELLOW}   ⚠️  Secret $secret non trouvé${NC}"
            echo "   Créez-le avec:"
            echo "   echo -n 'votre-valeur' | gcloud secrets create $secret --data-file=-"
        else
            echo "   ✓ Secret $secret existe"
        fi
    done
}

# Build de l'image Docker
build_image() {
    echo ""
    echo "🏗️  Build de l'image Docker..."
    
    docker build -t $IMAGE_NAME:latest .
    
    echo -e "${GREEN}✅ Image construite${NC}"
}

# Push vers Container Registry
push_image() {
    echo ""
    echo "📤 Push vers Google Container Registry..."
    
    # Authentification Docker vers GCR
    gcloud auth configure-docker --quiet
    
    docker push $IMAGE_NAME:latest
    
    echo -e "${GREEN}✅ Image pushée${NC}"
}

# Déploiement sur Cloud Run
deploy_cloudrun() {
    echo ""
    echo "☁️  Déploiement sur Cloud Run..."
    
    gcloud run deploy $SERVICE_NAME \
        --image $IMAGE_NAME:latest \
        --platform managed \
        --region $REGION \
        --memory 2Gi \
        --cpu 2 \
        --timeout 3600 \
        --concurrency 1 \
        --max-instances 1 \
        --set-env-vars "GCS_BUCKET_NAME=bodyminute-docs-storage" \
        --set-env-vars "EMBEDDINGS_PROVIDER=vertex" \
        --set-env-vars "VERTEX_AI_LOCATION=$REGION" \
        --set-env-vars "QDRANT_COLLECTION_NAME=mina_documents" \
        --set-env-vars "LOG_LEVEL=INFO" \
        --set-secrets "QDRANT_URL=QDRANT_URL:latest" \
        --set-secrets "QDRANT_API_KEY=QDRANT_API_KEY:latest" \
        --service-account "mina-indexer@${PROJECT_ID}.iam.gserviceaccount.com" \
        --no-allow-unauthenticated \
        --quiet
    
    echo -e "${GREEN}✅ Déploiement réussi!${NC}"
}

# Création du service account
create_service_account() {
    echo ""
    echo "👤 Configuration du Service Account..."
    
    SA_NAME="mina-indexer"
    SA_EMAIL="${SA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"
    
    # Créer le service account s'il n'existe pas
    if ! gcloud iam service-accounts describe $SA_EMAIL --project=$PROJECT_ID &> /dev/null; then
        gcloud iam service-accounts create $SA_NAME \
            --display-name="Mina Indexer Service Account" \
            --project=$PROJECT_ID
        echo "   ✓ Service Account créé"
    else
        echo "   ✓ Service Account existe déjà"
    fi
    
    # Attribuer les rôles nécessaires
    ROLES=(
        "roles/storage.objectViewer"
        "roles/aiplatform.user"
        "roles/secretmanager.secretAccessor"
    )
    
    for role in "${ROLES[@]}"; do
        gcloud projects add-iam-policy-binding $PROJECT_ID \
            --member="serviceAccount:$SA_EMAIL" \
            --role="$role" \
            --quiet &> /dev/null
        echo "   ✓ Rôle $role attribué"
    done
    
    echo -e "${GREEN}✅ Service Account configuré${NC}"
}

# Afficher le résumé
show_summary() {
    echo ""
    echo -e "${GREEN}=============================================="
    echo " ✅ DÉPLOIEMENT TERMINÉ"
    echo "=============================================="
    echo -e "${NC}"
    echo ""
    echo "📋 Résumé:"
    echo "   Projet:  $PROJECT_ID"
    echo "   Région:  $REGION"
    echo "   Service: $SERVICE_NAME"
    echo "   Image:   $IMAGE_NAME"
    echo ""
    echo "🔗 Pour lancer l'indexation manuellement:"
    echo "   gcloud run jobs execute $SERVICE_NAME --region=$REGION"
    echo ""
    echo "📊 Pour voir les logs:"
    echo "   gcloud run jobs logs $SERVICE_NAME --region=$REGION"
    echo ""
}

# Fonction principale
main() {
    check_prerequisites
    setup_gcloud
    create_service_account
    setup_secrets
    build_image
    push_image
    deploy_cloudrun
    show_summary
}

# Exécution
main "$@"
