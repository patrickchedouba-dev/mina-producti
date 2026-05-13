#!/usr/bin/env python3
"""
Déploiement automatisé Mina sur Google Cloud Run via APIs Python.
Projet: bodycoachocr

Ce script:
1. Crée les secrets dans Secret Manager
2. Soumet le build Docker à Cloud Build
3. Déploie un Cloud Run Job
4. Exécute le job d'indexation
"""

import os
import sys
import time
import tarfile
import io
from pathlib import Path

# Configuration
PROJECT_ID = "bodycoachocr"
REGION = "europe-west1"
JOB_NAME = "mina-indexer"
IMAGE_NAME = f"gcr.io/{PROJECT_ID}/{JOB_NAME}"

# Secrets Qdrant
QDRANT_URL = "https://729d910f-a0c0-43e0-8441-8afb3fcf5ec1.europe-west3-0.gcp.cloud.qdrant.io:6333"
QDRANT_API_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJhY2Nlc3MiOiJtIn0.VS3rmVsSl0QhByrItM5-qYNpozlJyNXX1mL0qjvUilI"

# GCS Bucket pour les sources
GCS_BUCKET_NAME = "mina-pdfs"


def check_dependencies():
    """Vérifie que les dépendances sont installées."""
    required = [
        "google.cloud.secretmanager",
        "google.cloud.devtools.cloudbuild_v1",
        "google.cloud.run_v2",
        "google.cloud.storage",
    ]
    
    missing = []
    for module in required:
        try:
            __import__(module)
        except ImportError:
            missing.append(module.replace(".", "-").replace("_", "-"))
    
    if missing:
        print("❌ Dépendances manquantes. Installation...")
        import subprocess
        packages = [
            "google-cloud-secret-manager",
            "google-cloud-build",
            "google-cloud-run",
            "google-cloud-storage",
        ]
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-q"] + packages)
        print("✅ Dépendances installées")


def create_secret(secret_id: str, secret_value: str) -> bool:
    """Crée un secret dans Secret Manager."""
    from google.cloud import secretmanager
    from google.api_core import exceptions
    
    client = secretmanager.SecretManagerServiceClient()
    parent = f"projects/{PROJECT_ID}"
    
    # Vérifier si le secret existe
    try:
        client.get_secret(request={"name": f"{parent}/secrets/{secret_id}"})
        print(f"   ℹ️  Secret {secret_id} existe déjà")
        return True
    except exceptions.NotFound:
        pass
    
    # Créer le secret
    try:
        client.create_secret(
            request={
                "parent": parent,
                "secret_id": secret_id,
                "secret": {"replication": {"automatic": {}}},
            }
        )
        print(f"   ✅ Secret {secret_id} créé")
    except exceptions.AlreadyExists:
        print(f"   ℹ️  Secret {secret_id} existe déjà")
    
    # Ajouter la version avec la valeur
    try:
        client.add_secret_version(
            request={
                "parent": f"{parent}/secrets/{secret_id}",
                "payload": {"data": secret_value.encode("utf-8")},
            }
        )
        print(f"   ✅ Version ajoutée pour {secret_id}")
        return True
    except Exception as e:
        print(f"   ❌ Erreur: {e}")
        return False


def setup_secrets():
    """Configure les secrets Qdrant dans Secret Manager."""
    print("\n📝 Configuration des secrets...")
    
    create_secret("QDRANT_URL", QDRANT_URL)
    create_secret("QDRANT_API_KEY", QDRANT_API_KEY)
    
    print("   ✅ Secrets configurés")


def create_source_tarball(source_dir: str) -> bytes:
    """Crée une archive tar.gz des sources pour Cloud Build."""
    print("\n📦 Création de l'archive source...")
    
    buffer = io.BytesIO()
    
    # Fichiers à exclure
    exclude_dirs = {"venv", "__pycache__", ".git", "tests", "docs", ".env"}
    exclude_files = {".env", ".DS_Store"}
    
    with tarfile.open(fileobj=buffer, mode="w:gz") as tar:
        source_path = Path(source_dir)
        
        # Fichiers racine essentiels
        root_files = ["Dockerfile", "requirements.txt", ".dockerignore"]
        for fname in root_files:
            fpath = source_path / fname
            if fpath.exists():
                tar.add(fpath, arcname=fname)
                print(f"   + {fname}")
        
        # Dossier backend/
        backend_dir = source_path / "backend"
        if backend_dir.exists():
            for item in backend_dir.rglob("*.py"):
                if "__pycache__" not in str(item):
                    rel_path = item.relative_to(source_path)
                    tar.add(item, arcname=str(rel_path))
                    print(f"   + {rel_path}")
        
        # Dossier scripts/ (créer un __init__.py vide pour éviter l'erreur)
        scripts_dir = source_path / "scripts"
        if scripts_dir.exists():
            for item in scripts_dir.glob("*.py"):
                if "__pycache__" not in str(item) and "deploy" not in item.name:
                    rel_path = item.relative_to(source_path)
                    tar.add(item, arcname=str(rel_path))
                    print(f"   + {rel_path}")
        
        # Créer un fichier vide scripts/__init__.py si nécessaire
        init_info = tarfile.TarInfo(name="scripts/__init__.py")
        init_info.size = 0
        tar.addfile(init_info, io.BytesIO(b""))
        print(f"   + scripts/__init__.py (créé)")
    
    buffer.seek(0)
    print(f"   ✅ Archive créée: {len(buffer.getvalue())} bytes")
    return buffer.getvalue()


def upload_source_to_gcs(source_bytes: bytes) -> str:
    """Upload les sources vers GCS pour Cloud Build."""
    from google.cloud import storage
    
    print("\n☁️  Upload des sources vers GCS...")
    
    bucket_name = f"{PROJECT_ID}_cloudbuild"
    blob_name = f"source/mina-indexer-{int(time.time())}.tar.gz"
    
    client = storage.Client(project=PROJECT_ID)
    
    # Créer le bucket s'il n'existe pas
    try:
        bucket = client.get_bucket(bucket_name)
    except Exception:
        print(f"   Création du bucket {bucket_name}...")
        bucket = client.create_bucket(bucket_name, location=REGION)
    
    blob = bucket.blob(blob_name)
    blob.upload_from_string(source_bytes, content_type="application/gzip")
    
    gcs_uri = f"gs://{bucket_name}/{blob_name}"
    print(f"   ✅ Sources uploadées: {gcs_uri}")
    
    return gcs_uri


def submit_build(source_gcs_uri: str) -> str:
    """Soumet le build à Cloud Build."""
    from google.cloud.devtools import cloudbuild_v1
    
    print("\n🏗️  Soumission du build Docker...")
    
    client = cloudbuild_v1.CloudBuildClient()
    
    # Extraire bucket et object du GCS URI
    parts = source_gcs_uri.replace("gs://", "").split("/", 1)
    bucket = parts[0]
    obj = parts[1]
    
    build = cloudbuild_v1.Build(
        source=cloudbuild_v1.Source(
            storage_source=cloudbuild_v1.StorageSource(
                bucket=bucket,
                object_=obj,
            )
        ),
        steps=[
            cloudbuild_v1.BuildStep(
                name="gcr.io/cloud-builders/docker",
                args=["build", "-t", IMAGE_NAME, "."],
            ),
            cloudbuild_v1.BuildStep(
                name="gcr.io/cloud-builders/docker",
                args=["push", IMAGE_NAME],
            ),
        ],
        images=[IMAGE_NAME],
        timeout={"seconds": 1200},  # 20 minutes
    )
    
    operation = client.create_build(project_id=PROJECT_ID, build=build)
    print(f"   ⏳ Build en cours... (ID: {operation.metadata.build.id})")
    
    # Attendre la fin du build
    result = operation.result(timeout=1200)
    
    if result.status == cloudbuild_v1.Build.Status.SUCCESS:
        print(f"   ✅ Build réussi! Image: {IMAGE_NAME}")
        return IMAGE_NAME
    else:
        print(f"   ❌ Build échoué: {result.status}")
        raise Exception(f"Build failed with status: {result.status}")


def create_cloud_run_job():
    """Crée un Cloud Run Job pour l'indexation."""
    from google.cloud import run_v2
    
    print("\n☁️  Création du Cloud Run Job...")
    
    client = run_v2.JobsClient()
    parent = f"projects/{PROJECT_ID}/locations/{REGION}"
    
    job = run_v2.Job(
        template=run_v2.ExecutionTemplate(
            template=run_v2.TaskTemplate(
                containers=[
                    run_v2.Container(
                        image=IMAGE_NAME,
                        resources=run_v2.ResourceRequirements(
                            limits={"memory": "2Gi", "cpu": "2"}
                        ),
                        env=[
                            run_v2.EnvVar(name="GCS_BUCKET_NAME", value=GCS_BUCKET_NAME),
                            run_v2.EnvVar(name="QDRANT_COLLECTION_NAME", value="bodyminute_docs"),
                            run_v2.EnvVar(name="EMBEDDINGS_PROVIDER", value="vertex"),
                            run_v2.EnvVar(name="VERTEX_AI_LOCATION", value=REGION),
                            run_v2.EnvVar(name="LOG_LEVEL", value="INFO"),
                            run_v2.EnvVar(
                                name="QDRANT_URL",
                                value_source=run_v2.EnvVarSource(
                                    secret_key_ref=run_v2.SecretKeySelector(
                                        secret=f"projects/{PROJECT_ID}/secrets/QDRANT_URL",
                                        version="latest",
                                    )
                                ),
                            ),
                            run_v2.EnvVar(
                                name="QDRANT_API_KEY",
                                value_source=run_v2.EnvVarSource(
                                    secret_key_ref=run_v2.SecretKeySelector(
                                        secret=f"projects/{PROJECT_ID}/secrets/QDRANT_API_KEY",
                                        version="latest",
                                    )
                                ),
                            ),
                        ],
                    )
                ],
                timeout={"seconds": 3600},  # 1 heure
                max_retries=1,
            ),
            task_count=1,
        ),
    )
    
    # Supprimer le job existant s'il existe
    try:
        client.delete_job(name=f"{parent}/jobs/{JOB_NAME}")
        print(f"   ℹ️  Job existant supprimé")
        time.sleep(5)
    except Exception:
        pass
    
    # Créer le job
    operation = client.create_job(
        parent=parent,
        job=job,
        job_id=JOB_NAME,
    )
    
    result = operation.result()
    print(f"   ✅ Job créé: {result.name}")
    return result.name


def execute_job(job_name: str):
    """Exécute le Cloud Run Job."""
    from google.cloud import run_v2
    
    print("\n🚀 Lancement de l'indexation...")
    
    client = run_v2.JobsClient()
    
    operation = client.run_job(name=job_name)
    
    print(f"   ⏳ Exécution en cours...")
    print(f"   📊 Suivre dans la console:")
    print(f"   https://console.cloud.google.com/run/jobs/details/{REGION}/{JOB_NAME}?project={PROJECT_ID}")
    
    # Ne pas attendre la fin (peut prendre longtemps)
    print(f"\n   ✅ Job lancé! L'indexation tourne en arrière-plan.")
    print(f"   📊 Vérifiez les logs dans la console GCP.")


def main():
    """Point d'entrée principal."""
    print("=" * 60)
    print("🚀 DÉPLOIEMENT MINA - Cloud Run via API Python")
    print(f"   Projet: {PROJECT_ID}")
    print(f"   Région: {REGION}")
    print("=" * 60)
    
    try:
        # Vérifier les dépendances
        check_dependencies()
        
        # 1. Configurer les secrets
        setup_secrets()
        
        # 2. Créer et uploader l'archive source
        source_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        source_bytes = create_source_tarball(source_dir)
        gcs_uri = upload_source_to_gcs(source_bytes)
        
        # 3. Soumettre le build
        submit_build(gcs_uri)
        
        # 4. Créer le Cloud Run Job
        job_name = create_cloud_run_job()
        
        # 5. Exécuter le job
        execute_job(job_name)
        
        print("\n" + "=" * 60)
        print("✅ DÉPLOIEMENT TERMINÉ!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ Erreur: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
