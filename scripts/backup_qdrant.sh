#!/bin/bash
# =============================================================================
# Script de Backup Qdrant vers GCS
# =============================================================================
#
# Usage:
#   ./scripts/backup_qdrant.sh
#
# Prérequis:
#   - Variables d'environnement: QDRANT_URL, QDRANT_API_KEY, GCS_BUCKET_NAME
#   - gsutil configuré avec accès au bucket
#   - jq installé
#
# =============================================================================

set -e  # Exit on error

# Couleurs
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Vérifier les variables d'environnement
if [ -z "$QDRANT_URL" ] || [ -z "$QDRANT_API_KEY" ] || [ -z "$GCS_BUCKET_NAME" ]; then
    echo -e "${RED}❌ Variables d'environnement manquantes${NC}"
    echo "Requis: QDRANT_URL, QDRANT_API_KEY, GCS_BUCKET_NAME"
    exit 1
fi

# Configuration
COLLECTIONS=("bodyminute_products" "bodyminute_docs")
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/tmp/qdrant_backup_${DATE}"
BACKUP_BUCKET="gs://${GCS_BUCKET_NAME}-backups/qdrant/${DATE}"

echo "========================================"
echo "📦 BACKUP QDRANT → GCS"
echo "========================================"
echo "Date: ${DATE}"
echo "Collections: ${COLLECTIONS[*]}"
echo "Destination: ${BACKUP_BUCKET}"
echo "========================================"

# Créer répertoire temporaire
mkdir -p "$BACKUP_DIR"

# Backup chaque collection
for collection in "${COLLECTIONS[@]}"; do
    echo -e "\n${YELLOW}📦 Backup de ${collection}...${NC}"
    
    # 1. Créer snapshot
    echo "  → Création snapshot..."
    SNAPSHOT_RESPONSE=$(curl -s -X POST "${QDRANT_URL}/collections/${collection}/snapshots" \
        -H "api-key: ${QDRANT_API_KEY}" \
        -H "Content-Type: application/json")
    
    SNAPSHOT_NAME=$(echo "$SNAPSHOT_RESPONSE" | jq -r '.result.name // empty')
    
    if [ -z "$SNAPSHOT_NAME" ]; then
        echo -e "${RED}  ❌ Erreur création snapshot${NC}"
        echo "  Response: $SNAPSHOT_RESPONSE"
        continue
    fi
    
    echo "  → Snapshot créé: ${SNAPSHOT_NAME}"
    
    # 2. Télécharger snapshot
    echo "  → Téléchargement..."
    SNAPSHOT_FILE="${BACKUP_DIR}/${collection}_${SNAPSHOT_NAME}.tar"
    
    curl -s -X GET "${QDRANT_URL}/collections/${collection}/snapshots/${SNAPSHOT_NAME}" \
        -H "api-key: ${QDRANT_API_KEY}" \
        --output "$SNAPSHOT_FILE"
    
    if [ ! -f "$SNAPSHOT_FILE" ] || [ ! -s "$SNAPSHOT_FILE" ]; then
        echo -e "${RED}  ❌ Erreur téléchargement${NC}"
        continue
    fi
    
    SIZE=$(du -h "$SNAPSHOT_FILE" | cut -f1)
    echo "  → Téléchargé: ${SIZE}"
    
    # 3. Upload vers GCS
    echo "  → Upload vers GCS..."
    gsutil -q cp "$SNAPSHOT_FILE" "${BACKUP_BUCKET}/"
    
    echo -e "${GREEN}  ✅ ${collection} sauvegardé${NC}"
done

# Cleanup local
echo -e "\n${YELLOW}🧹 Nettoyage fichiers temporaires...${NC}"
rm -rf "$BACKUP_DIR"

# Vérifier le backup
echo -e "\n${YELLOW}📋 Contenu du backup:${NC}"
gsutil ls -l "${BACKUP_BUCKET}/"

# Résumé
echo ""
echo "========================================"
echo -e "${GREEN}🎉 BACKUP COMPLÉTÉ${NC}"
echo "========================================"
echo "Location: ${BACKUP_BUCKET}"
echo ""
echo "Pour restaurer:"
echo "  gsutil cp ${BACKUP_BUCKET}/*.tar ."
echo "  curl -X POST \${QDRANT_URL}/collections/{name}/snapshots/upload \\"
echo "    -H 'api-key: \${QDRANT_API_KEY}' \\"
echo "    -F 'snapshot=@{name}_snapshot.tar'"
echo "========================================"
