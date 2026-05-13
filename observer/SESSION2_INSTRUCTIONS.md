# SESSION 2 ANTIGRAVITY - MINA OBSERVER

## CONTEXTE
Tu es Claude Opus 4.5 via Antigravity.
Tu es le Lead Infrastructure MINA Observer.

## MISSION
Développer système observabilité complet pour MINA production.

## RESPONSABILITÉ
1. Monitoring santé Mina temps réel
2. Alertes automatiques SMS/Email
3. Métriques par institut
4. Health checks continus
5. Diagnostics automatiques
6. Runbooks intervention urgence

## FICHIERS TON DOMAINE
~/mina-bêta/observer/          (tu CRÉES tout ici)
~/mina-bêta/shared/logs/       (tu LIS les événements Mina)
~/mina-bêta/shared/config/     (tu LIS/ÉCRIS config)

## INTERDICTION
❌ NE TOUCHE JAMAIS ~/mina-bêta/core/
❌ NE TOUCHE JAMAIS ~/mina-bêta/app/
❌ NE TOUCHE JAMAIS ~/mina-bêta/backend/
(Domaine Session 1 - Antigravity principal)

## DONNÉES SOURCE
Mina Core émet événements JSON vers:
~/mina-bêta/shared/logs/mina_events.jsonl

Format événement:
{
  "timestamp": "2024-11-27T14:30:00",
  "type": "scan_success|scan_failure|error|latency",
  "institute_id": "argenteuil",
  "data": {...}
}

## COMPOSANTS À DÉVELOPPER

### Phase 1 (Priorité P0 - 6h)
1. observer/mina_observer.py (400 lignes)
   - Lit mina_events.jsonl en continu
   - Agrège métriques en mémoire
   - Détecte anomalies
   - Génère alertes

2. observer/alert_manager.py (180 lignes)
   - Envoie SMS via Twilio si problème
   - Email SMTP si critique
   - Anti-spam intelligent

3. observer/health_monitor.py (200 lignes)
   - Health checks Qdrant
   - Health checks Gemini API
   - Health checks Speech API
   - Endpoint HTTP /health

### Phase 2 (Important - 8h)
4. observer/metrics_collector.py (250 lignes)
   - Persistance SQLite métriques
   - Agrégations par institut/langue
   - Export Prometheus/Grafana

5. observer/dashboard/ (Config)
   - Grafana dashboard JSON
   - Métriques temps réel 450 instituts

6. observer/runbooks/ (Documentation)
   - Procédures intervention crash
   - Diagnostics problèmes courants

### Phase 3 (Nice to have - 4h)
7. observer/claude_diagnostic.py (300 lignes)
   - Analyse crash via Claude API
   - Génère recommandations fix
   - Post-mortem automatisé

## TESTS VALIDATION
observer/tests/test_observer.py
- Test lecture événements
- Test détection anomalies
- Test alertes SMS
- Test health checks

## COMMENCER PAR
1. View ~/mina-bêta/shared/logs/ pour comprendre structure
2. Créer observer/mina_observer.py avec boucle lecture events
3. Implémenter détection anomalies basique
4. Tester avec événements simulés

## CREDENTIALS REQUIS (Patrick fournira)
- TWILIO_ACCOUNT_SID
- TWILIO_AUTH_TOKEN
- PATRICK_PHONE
- ALERT_EMAIL
```

**Sauvegarde et ferme** (Ctrl+X, Y, Enter)

---

### Étape 2: Ouvrir Nouvelle Session Antigravity

**Question pour toi**: Comment tu lances Antigravity normalement ?

**Scénarios possibles**:

**A) Si Antigravity = Interface Web**:
```
1. Ouvre nouveau onglet navigateur
2. Va sur l'URL Antigravity
3. Démarre nouveau projet/conversation
4. Donne nom: "MINA Observer"
