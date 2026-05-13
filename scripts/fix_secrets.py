#!/usr/bin/env python3
"""
Mise à jour des secrets et relance du job.
"""

import sys
import time

PROJECT_ID = "bodycoachocr"
REGION = "europe-west1"
JOB_NAME = "mina-indexer"

# Valeurs CORRECTES des secrets
QDRANT_URL = "https://729d910f-a0c0-43e0-8441-8afb3fcf5ec1.europe-west3-0.gcp.cloud.qdrant.io:6333"
QDRANT_API_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJhY2Nlc3MiOiJtIn0.VS3rmVsSl0QhByrItM5-qYNpozlJyNXX1mL0qjvUilI"


def update_secret(secret_id: str, secret_value: str):
    """Met à jour la valeur d'un secret existant."""
    from google.cloud import secretmanager
    
    client = secretmanager.SecretManagerServiceClient()
    parent = f"projects/{PROJECT_ID}/secrets/{secret_id}"
    
    print(f"📝 Mise à jour du secret {secret_id}...")
    
    # Ajouter une nouvelle version
    response = client.add_secret_version(
        request={
            "parent": parent,
            "payload": {"data": secret_value.encode("utf-8")},
        }
    )
    
    print(f"   ✅ Nouvelle version: {response.name}")
    
    # Vérifier que la valeur est correcte
    version = client.access_secret_version(request={"name": f"{response.name}"})
    stored_value = version.payload.data.decode("utf-8")
    
    if stored_value == secret_value:
        print(f"   ✅ Valeur vérifiée: {stored_value[:50]}...")
    else:
        print(f"   ❌ ERREUR: Valeur différente!")
        print(f"      Attendu: {secret_value[:50]}")
        print(f"      Stocké:  {stored_value[:50]}")


def run_job():
    """Relance le job Cloud Run."""
    from google.cloud import run_v2
    
    print(f"\n🚀 Relance du job {JOB_NAME}...")
    
    client = run_v2.JobsClient()
    job_name = f"projects/{PROJECT_ID}/locations/{REGION}/jobs/{JOB_NAME}"
    
    operation = client.run_job(name=job_name)
    
    print(f"   ⏳ Exécution lancée")
    print(f"   📊 Suivre: https://console.cloud.google.com/run/jobs/details/{REGION}/{JOB_NAME}?project={PROJECT_ID}")


def main():
    print("=" * 60)
    print("🔧 CORRECTION DES SECRETS QDRANT")
    print("=" * 60)
    
    # Mettre à jour les secrets
    update_secret("QDRANT_URL", QDRANT_URL)
    update_secret("QDRANT_API_KEY", QDRANT_API_KEY)
    
    # Attendre que les secrets soient propagés
    print("\n⏳ Attente propagation des secrets (10s)...")
    time.sleep(10)
    
    # Relancer le job
    run_job()
    
    print("\n" + "=" * 60)
    print("✅ Secrets corrigés et job relancé!")
    print("=" * 60)


if __name__ == "__main__":
    main()
