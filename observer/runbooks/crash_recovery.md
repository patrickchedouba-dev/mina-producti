# MINA Observer - Runbook Crash Recovery

**Version** : 1.0  
**Date** : 23 décembre 2024  
**Classification** : Opérationnel

---

## 1. PROCÉDURES D'URGENCE

### 1.1 MINA ne répond plus (500 errors)

**Symptômes :**
- Interface bloquée ou erreurs 500
- Logs : `ConnectionError`, `TimeoutError`, `ServiceUnavailable`

**Actions immédiates (< 5 min) :**

```bash
# 1. Vérifier status services
cd ~/mina-bêta
python observer/health_monitor.py --check

# 2. Si Qdrant down
curl -s http://localhost:6333/health
# Si échec → Redémarrer Qdrant
docker restart qdrant

# 3. Si Cloud Run down
gcloud run services describe mina-streamlit --region=europe-west1
# Si échec → Redéployer
gcloud run deploy mina-streamlit --image=gcr.io/$PROJECT/mina-streamlit

# 4. Vérifier logs
gcloud run services logs read mina-streamlit --tail=50
```

**Escalation si échec :** Contacter Google Cloud Support

---

### 1.2 Latence > 10 secondes

**Symptômes :**
- Utilisateurs rapportent lenteur extrême
- Alerte Observer `latency_critical`

**Actions immédiates :**

```bash
# 1. Identifier étape lente
python observer/mina_observer.py --summary

# 2. Vérifier Qdrant
curl -s "${QDRANT_URL}/telemetry" -H "api-key: ${QDRANT_API_KEY}"
# Si latence > 100ms → Bottleneck DB

# 3. Vérifier quotas GCP
gcloud ml speech recognize-quota --format=json

# 4. Mitigation temporaire
gcloud run services update mina-streamlit --min-instances=2 --cpu=2
```

**Solutions permanentes :**
- Upgrade Qdrant (Starter → Pro)
- Augmenter quotas Speech/TTS API
- Optimiser embeddings caching

---

### 1.3 Erreurs consécutives (> 5)

**Symptômes :**
- Alerte `consecutive_errors`
- Un institut spécifique affecté

**Diagnostic :**

```bash
# Identifier institut affecté
python -c "
from observer.mina_observer import MinaObserver
obs = MinaObserver()
events = obs.read_events(0)
for e in events:
    obs.process_event(e)
for k, v in obs.metrics.items():
    if v.consecutive_errors >= 5:
        print(f'ALERTE: {k} = {v.consecutive_errors} erreurs consécutives')
"

# Vérifier logs institut
grep "institut_id" shared/logs/mina_events.jsonl | tail -20
```

**Actions :**
- Si problème réseau institut → Contacter institut
- Si bug code → Rollback version précédente

---

## 2. ROLLBACK

### 2.1 Rollback Cloud Run

```bash
# Lister révisions disponibles
gcloud run revisions list --service=mina-streamlit --region=europe-west1

# Basculer vers révision stable
gcloud run services update-traffic mina-streamlit \
  --to-revisions=mina-streamlit-00005-abc=100 \
  --region=europe-west1

# Vérifier
curl -s https://mina-streamlit-xxx.run.app/health
```

### 2.2 Rollback Qdrant

```bash
# Lister snapshots disponibles
gsutil ls gs://${GCS_BUCKET_NAME}-backups/qdrant/

# Restaurer dernier snapshot
./scripts/backup_qdrant.sh --restore 20241223

# Vérifier intégrité
curl -s "${QDRANT_URL}/collections" -H "api-key: ${QDRANT_API_KEY}"
```

---

## 3. REDÉMARRAGES

### 3.1 Redémarrer Observer

```bash
# Arrêter (si en cours)
pkill -f "mina_observer.py"

# Redémarrer en background
nohup python observer/mina_observer.py --watch > /tmp/observer.log 2>&1 &

# Vérifier
tail -f /tmp/observer.log
```

### 3.2 Redémarrer Health Server

```bash
# Arrêter
pkill -f "health_monitor.py"

# Redémarrer
nohup python observer/health_monitor.py --serve --port 8080 > /tmp/health.log 2>&1 &

# Tester
curl -s http://localhost:8080/health
```

### 3.3 Redémarrer Mina Streamlit (local)

```bash
cd ~/mina-bêta
source venv/bin/activate

# Kill existant
pkill -f "streamlit run"

# Redémarrer
nohup streamlit run scripts/app_chatbot.py --server.port 8501 > /tmp/mina.log 2>&1 &

# Vérifier
curl -s http://localhost:8501/health
```

---

## 4. VÉRIFICATIONS POST-INCIDENT

### 4.1 Checklist Retour Normal

- [ ] Health check OK (`python observer/health_monitor.py --check`)
- [ ] Observer running (`ps aux | grep mina_observer`)
- [ ] Tests passent (`python -m pytest tests/ -v`)
- [ ] Logs sans erreurs (`tail -50 shared/logs/mina_events.jsonl`)
- [ ] Métriques normales (`python observer/mina_observer.py --summary`)

### 4.2 Créer Post-Mortem

```bash
# Template
cat > ~/mina-bêta/observer/runbooks/postmortems/$(date +%Y%m%d)_incident.md << 'EOF'
# Post-Mortem: [Titre]

**Date**: $(date)
**Durée**: X minutes
**Sévérité**: P0 / P1 / P2

## Chronologie
- HH:MM - Détection
- HH:MM - Diagnostic
- HH:MM - Résolution

## Cause Racine
[Description]

## Actions Correctives
- [ ] Action 1
- [ ] Action 2

## Leçons Apprises
[Ce qui a bien/mal fonctionné]
EOF
```

---

## 5. CONTACTS ESCALATION

| Niveau | Contact | Délai |
|--------|---------|-------|
| L1 - Observer | Alertes automatiques | Immédiat |
| L2 - Tech Lead | Patrick Chedouba | < 15 min |
| L3 - Cloud Support | Google Cloud | < 1h |
| L4 - Business | Direction Body Minute | < 4h |

---

## 6. COMMANDES RAPIDES

```bash
# Status rapide
python observer/health_monitor.py --check

# Observer summary
python observer/mina_observer.py --summary

# Logs récents
tail -50 shared/logs/mina_events.jsonl | jq

# Test connectivité
python observer/alert_manager.py --test

# Métriques
python observer/metrics_collector.py --demo && python observer/metrics_collector.py
```

---

*Document opérationnel - MINA Observer*
