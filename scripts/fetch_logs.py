#!/usr/bin/env python3
"""
Récupération des logs Cloud Run Job via API Cloud Logging.
"""

import sys
from datetime import datetime, timedelta

PROJECT_ID = "bodycoachocr"
JOB_NAME = "mina-indexer"


def fetch_logs():
    """Récupère les logs du job Cloud Run."""
    from google.cloud import logging as cloud_logging
    
    print(f"\n📋 LOGS DU JOB: {JOB_NAME}")
    print("=" * 60)
    
    client = cloud_logging.Client(project=PROJECT_ID)
    
    # Filtrer les logs du job Cloud Run des dernières 24h
    filter_str = f'''
        resource.type="cloud_run_job"
        resource.labels.job_name="{JOB_NAME}"
        timestamp >= "{(datetime.utcnow() - timedelta(hours=24)).isoformat()}Z"
    '''
    
    print(f"Filtre: {filter_str.strip()}")
    print("-" * 60)
    
    entries = list(client.list_entries(filter_=filter_str, max_results=100))
    
    if not entries:
        print("\n⚠️  AUCUN LOG TROUVÉ!")
        print("\nCauses possibles:")
        print("  1. Le job n'a pas été exécuté correctement")
        print("  2. Les logs n'ont pas été transmis")
        print("  3. Le container a crashé avant d'écrire des logs")
        
        # Essayer avec un filtre plus large
        print("\n🔍 Tentative avec filtre élargi...")
        filter_str2 = f'''
            resource.type="cloud_run_job"
            timestamp >= "{(datetime.utcnow() - timedelta(hours=24)).isoformat()}Z"
        '''
        entries2 = list(client.list_entries(filter_=filter_str2, max_results=50))
        
        if entries2:
            print(f"\n📋 {len(entries2)} logs trouvés (tous jobs):")
            for entry in entries2[:20]:
                print(f"  [{entry.timestamp}] {entry.payload}")
        else:
            print("  Aucun log Cloud Run Job dans les 24h")
        
        return False
    
    print(f"\n✅ {len(entries)} logs trouvés:\n")
    
    for entry in entries:
        timestamp = entry.timestamp.strftime("%H:%M:%S") if entry.timestamp else "?"
        severity = entry.severity or "INFO"
        
        # Extraire le message
        if isinstance(entry.payload, dict):
            message = entry.payload.get("message", str(entry.payload))
        else:
            message = str(entry.payload)
        
        print(f"[{timestamp}] {severity}: {message[:200]}")
    
    return True


def check_execution_history():
    """Vérifie l'historique des exécutions du job."""
    from google.cloud import run_v2
    
    print("\n\n📊 HISTORIQUE DES EXÉCUTIONS")
    print("=" * 60)
    
    client = run_v2.ExecutionsClient()
    parent = f"projects/{PROJECT_ID}/locations/europe-west1/jobs/{JOB_NAME}"
    
    try:
        executions = list(client.list_executions(parent=parent))
        
        if not executions:
            print("Aucune exécution trouvée")
            return
        
        for ex in executions[:5]:
            print(f"\n🔹 Exécution: {ex.name.split('/')[-1]}")
            print(f"   Status: {ex.conditions}")
            print(f"   Créée: {ex.create_time}")
            print(f"   Terminée: {ex.completion_time}")
            
            # Vérifier les tâches
            if hasattr(ex, 'failed_count'):
                print(f"   Échouées: {ex.failed_count}")
            if hasattr(ex, 'succeeded_count'):
                print(f"   Réussies: {ex.succeeded_count}")
                
    except Exception as e:
        print(f"Erreur: {e}")


if __name__ == "__main__":
    try:
        # Installer la dépendance si nécessaire
        try:
            from google.cloud import logging
        except ImportError:
            import subprocess
            subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", "google-cloud-logging"])
        
        fetch_logs()
        check_execution_history()
        
    except Exception as e:
        print(f"❌ Erreur: {e}")
        import traceback
        traceback.print_exc()
