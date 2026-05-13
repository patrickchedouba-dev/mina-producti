# MINA Observer - Runbook Diagnostics

**Version** : 1.0  
**Date** : 23 décembre 2024

---

## 1. PROBLÈMES COURANTS

### 1.1 "Aucun événement dans mina_events.jsonl"

**Cause :** Mina n'écrit pas dans le fichier d'événements.

**Diagnostic :**
```bash
# Vérifier si fichier existe
ls -la shared/logs/mina_events.jsonl

# Vérifier permissions
stat shared/logs/

# Vérifier si Mina log les événements
grep "event" scripts/app_chatbot.py
```

**Solution :**
```python
# Ajouter dans app_chatbot.py après chaque interaction:
from observer.mina_observer import MinaEvent
import json
from datetime import datetime

def log_mina_event(event_type, latency_ms, success, **kwargs):
    event = {
        "timestamp": datetime.now().isoformat(),
        "event_type": event_type,
        "latency_ms": latency_ms,
        "success": success,
        **kwargs
    }
    with open("shared/logs/mina_events.jsonl", "a") as f:
        f.write(json.dumps(event) + "\n")
```

---

### 1.2 "Observer ne détecte pas les anomalies"

**Cause :** Seuils mal configurés ou pas assez d'échantillons.

**Diagnostic :**
```bash
# Vérifier seuils actuels
python -c "
from observer.mina_observer import THRESHOLDS
for k, v in THRESHOLDS.items():
    print(f'{k}: {v}')
"

# Compter événements
wc -l shared/logs/mina_events.jsonl
```

**Solution :** Ajuster les seuils dans `mina_observer.py` :
```python
THRESHOLDS = {
    "error_rate_percent": 5,    # Plus sensible
    "latency_critical_ms": 5000,  # Plus bas
    "consecutive_errors": 3,     # Moins tolérant
}
```

---

### 1.3 "Alertes SMS ne partent pas"

**Cause :** Twilio mal configuré.

**Diagnostic :**
```bash
# Tester config
python observer/alert_manager.py --test

# Vérifier variables
echo "SID: ${TWILIO_ACCOUNT_SID:0:10}..."
echo "FROM: $TWILIO_FROM_PHONE"
echo "TO: $ALERT_PHONE_NUMBERS"
```

**Solution :**
```bash
# Définir variables
export TWILIO_ACCOUNT_SID="ACxxxxx"
export TWILIO_AUTH_TOKEN="xxxx"
export TWILIO_FROM_PHONE="+33xxxxxxxxx"
export ALERT_PHONE_NUMBERS="+33xxxxxxxxx"

# Tester envoi
python observer/alert_manager.py --sms "Test MINA"
```

---

### 1.4 "Health check Qdrant échoue"

**Cause :** Qdrant inaccessible ou mauvaise URL.

**Diagnostic :**
```bash
# Vérifier URL
echo $QDRANT_URL

# Test direct
curl -s "${QDRANT_URL}/health" -H "api-key: ${QDRANT_API_KEY}"

# Docker local?
docker ps | grep qdrant
```

**Solutions :**
```bash
# Si Qdrant Cloud
export QDRANT_URL="https://xxx.cloud.qdrant.io:6333"
export QDRANT_API_KEY="xxx"

# Si Docker local
docker run -d -p 6333:6333 qdrant/qdrant
export QDRANT_URL="http://localhost:6333"
```

---

### 1.5 "Métriques incorrectes"

**Cause :** Données anciennes ou fenêtre trop large.

**Diagnostic :**
```bash
# Vérifier âge données
head -1 shared/logs/mina_events.jsonl | jq .timestamp
tail -1 shared/logs/mina_events.jsonl | jq .timestamp

# Compter récentes (dernière heure)
python -c "
import json
from datetime import datetime, timedelta
cutoff = datetime.now() - timedelta(hours=1)
count = 0
with open('shared/logs/mina_events.jsonl') as f:
    for line in f:
        data = json.loads(line)
        ts = datetime.fromisoformat(data['timestamp'].replace('Z', '+00:00'))
        if ts.replace(tzinfo=None) > cutoff:
            count += 1
print(f'Événements dernière heure: {count}')
"
```

**Solution :** Réduire fenêtre ou reset métriques :
```python
collector = MetricsCollector(window_seconds=60)  # 1 min
collector.reset()
```

---

## 2. INTERPRÉTATION ALERTES

### Types d'alertes Observer

| Catégorie | Niveau | Signification | Action |
|-----------|--------|---------------|--------|
| `error_rate` | critical | > 10% d'erreurs | Investiguer logs |
| `latency` | warning | 5-10s latence | Surveiller |
| `latency` | critical | > 10s latence | Action immédiate |
| `consecutive` | critical | 5+ erreurs de suite | Vérifier service |
| `health` | critical | Service down | Redémarrer |

### Lecture des logs

```bash
# Événements récents
tail -20 shared/logs/mina_events.jsonl | jq

# Filtrer erreurs
grep '"success":false' shared/logs/mina_events.jsonl | tail -10 | jq

# Par institut
grep '"institut_id":"BM-PARIS-01"' shared/logs/mina_events.jsonl | jq
```

---

## 3. TESTS MANUELS

### 3.1 Simuler événements

```bash
# Créer événements test
python -c "
import json
from datetime import datetime

events = [
    {'timestamp': datetime.now().isoformat(), 'event_type': 'request', 'latency_ms': 500, 'success': True, 'language': 'fr'},
    {'timestamp': datetime.now().isoformat(), 'event_type': 'request', 'latency_ms': 12000, 'success': True, 'language': 'fr'},  # Latence haute
    {'timestamp': datetime.now().isoformat(), 'event_type': 'error', 'latency_ms': 0, 'success': False, 'error_message': 'Timeout'},
]

with open('shared/logs/mina_events.jsonl', 'a') as f:
    for e in events:
        f.write(json.dumps(e) + '\n')

print(f'Ajouté {len(events)} événements test')
"
```

### 3.2 Tester Observer

```bash
# Mode résumé (lecture complète)
python observer/mina_observer.py --summary

# Mode watch (temps réel)
python observer/mina_observer.py --watch
# → Ajouter événements dans un autre terminal pour voir détection
```

### 3.3 Tester alertes

```bash
# Test email (si configuré)
python observer/alert_manager.py --email "Test diagnostic"

# Test SMS (si configuré)
python observer/alert_manager.py --sms "Test diagnostic"

# Test connectivité
python observer/alert_manager.py --test
```

---

## 4. COMMANDES DIAGNOSTIC

```bash
# === STATUS GLOBAL ===
echo "=== MINA Observer Status ==="
python observer/health_monitor.py --check
echo ""
python observer/mina_observer.py --summary

# === LOGS ===
echo "=== Derniers événements ==="
tail -10 shared/logs/mina_events.jsonl | jq -c

# === MÉTRIQUES ===
echo "=== Métriques ==="
python observer/metrics_collector.py

# === PROCESSUS ===
echo "=== Processus actifs ==="
ps aux | grep -E "(mina_observer|health_monitor|streamlit)" | grep -v grep
```

---

*Document diagnostic - MINA Observer*
