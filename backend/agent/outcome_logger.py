"""
Outcome Logger - Stockage des décisions contrefactuelles.

Stocke les décisions en PostgreSQL pour analyse différée (J+7, J+30).
Format optimisé pour calcul de regret futur.
"""

import os
import json
import logging
from typing import Dict, List, Optional
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

# Fallback: log fichier si PostgreSQL indisponible
OUTCOME_LOG_DIR = Path(__file__).parent.parent.parent / "logs" / "counterfactual"


class OutcomeLogger:
    """
    Logger des décisions contrefactuelles.
    
    Stocke:
    - Décision réelle (path A)
    - Chemins shadow (B1, B2, B3, B4)
    - Metadata pour tracking (session, client, institut)
    
    Pour analyse différée:
    - J+7: Cliente revenue ?
    - J+30: Fidélisation ?
    """
    
    def __init__(self):
        self._postgres = None
        self._initialized = False
        
        # Créer dossier logs fallback
        OUTCOME_LOG_DIR.mkdir(parents=True, exist_ok=True)
    
    def _ensure_init(self):
        if self._initialized:
            return
        
        try:
            from backend.memory import get_memory_system
            memory = get_memory_system()
            if hasattr(memory, '_postgres') and memory._postgres:
                self._postgres = memory._postgres
                self._ensure_table()
                logger.info("📊 OutcomeLogger: PostgreSQL connecté")
        except Exception as e:
            logger.warning(f"⚠️ OutcomeLogger: Fallback fichier ({e})")
        
        self._initialized = True
    
    def _ensure_table(self):
        """Crée la table si elle n'existe pas."""
        if not self._postgres:
            return
        
        try:
            self._postgres.execute("""
                CREATE TABLE IF NOT EXISTS counterfactual_decisions (
                    id SERIAL PRIMARY KEY,
                    decision_id VARCHAR(64) UNIQUE NOT NULL,
                    session_id VARCHAR(128),
                    client_id VARCHAR(128),
                    institut_id VARCHAR(64),
                    timestamp TIMESTAMP NOT NULL,
                    user_input TEXT,
                    real_path JSONB,
                    shadow_paths JSONB,
                    context JSONB,
                    outcome_7d JSONB DEFAULT NULL,
                    outcome_30d JSONB DEFAULT NULL,
                    regret_score FLOAT DEFAULT NULL,
                    created_at TIMESTAMP DEFAULT NOW()
                );
                
                CREATE INDEX IF NOT EXISTS idx_cf_session ON counterfactual_decisions(session_id);
                CREATE INDEX IF NOT EXISTS idx_cf_client ON counterfactual_decisions(client_id);
                CREATE INDEX IF NOT EXISTS idx_cf_institut ON counterfactual_decisions(institut_id);
                CREATE INDEX IF NOT EXISTS idx_cf_timestamp ON counterfactual_decisions(timestamp);
            """)
            logger.debug("📊 Table counterfactual_decisions OK")
        except Exception as e:
            logger.warning(f"⚠️ Create table: {e}")
    
    def log_decision(self, decision: "CounterfactualDecision") -> bool:
        """
        Log une décision contrefactuelle.
        
        Args:
            decision: Objet CounterfactualDecision
        
        Returns:
            True si succès
        """
        self._ensure_init()
        
        data = decision.to_dict()
        
        # Essayer PostgreSQL d'abord
        if self._postgres:
            try:
                self._postgres.execute("""
                    INSERT INTO counterfactual_decisions 
                    (decision_id, session_id, client_id, institut_id, timestamp, user_input, real_path, shadow_paths, context)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (decision_id) DO NOTHING
                """, (
                    data["decision_id"],
                    data["session_id"],
                    data["client_id"],
                    data["institut_id"],
                    data["timestamp"],
                    data["user_input"],
                    json.dumps(data["real_path"]),
                    json.dumps(data["shadow_paths"]),
                    json.dumps(data["context"])
                ))
                logger.info(f"📊 Logged decision {data['decision_id']} to PostgreSQL")
                return True
            except Exception as e:
                logger.warning(f"⚠️ PostgreSQL log: {e}")
        
        # Fallback fichier
        return self._log_to_file(data)
    
    def _log_to_file(self, data: Dict) -> bool:
        """Fallback: log en fichier JSONL."""
        try:
            date_str = datetime.now().strftime("%Y-%m-%d")
            log_file = OUTCOME_LOG_DIR / f"decisions_{date_str}.jsonl"
            
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(data, ensure_ascii=False) + "\n")
            
            logger.info(f"📊 Logged decision {data['decision_id']} to file")
            return True
        except Exception as e:
            logger.error(f"❌ File log: {e}")
            return False
    
    def update_outcome(
        self,
        decision_id: str,
        outcome_type: str,  # "7d" ou "30d"
        outcome_data: Dict
    ) -> bool:
        """
        Met à jour l'outcome d'une décision (appelé par batch job).
        
        Args:
            decision_id: ID décision
            outcome_type: "7d" ou "30d"
            outcome_data: {returned: bool, purchased: bool, basket: float, ...}
        """
        if not self._postgres:
            logger.warning("⚠️ update_outcome requires PostgreSQL")
            return False
        
        column = f"outcome_{outcome_type}"
        
        try:
            self._postgres.execute(f"""
                UPDATE counterfactual_decisions
                SET {column} = %s
                WHERE decision_id = %s
            """, (json.dumps(outcome_data), decision_id))
            
            logger.info(f"📊 Updated {outcome_type} outcome for {decision_id}")
            return True
        except Exception as e:
            logger.error(f"❌ Update outcome: {e}")
            return False
    
    def get_decisions_for_analysis(
        self,
        institut_id: Optional[str] = None,
        days_back: int = 30
    ) -> List[Dict]:
        """Récupère les décisions pour analyse."""
        if not self._postgres:
            return []
        
        try:
            query = """
                SELECT * FROM counterfactual_decisions
                WHERE timestamp > NOW() - INTERVAL '%s days'
            """
            params = [days_back]
            
            if institut_id:
                query += " AND institut_id = %s"
                params.append(institut_id)
            
            query += " ORDER BY timestamp DESC LIMIT 1000"
            
            result = self._postgres.fetch_all(query, params)
            return [dict(row) for row in result] if result else []
        except Exception as e:
            logger.error(f"❌ Fetch decisions: {e}")
            return []


# Singleton
_outcome_logger: Optional[OutcomeLogger] = None


def get_outcome_logger() -> OutcomeLogger:
    """Retourne l'instance singleton."""
    global _outcome_logger
    if _outcome_logger is None:
        _outcome_logger = OutcomeLogger()
    return _outcome_logger


# Import local pour éviter circular
from backend.agent.counterfactual import CounterfactualDecision
