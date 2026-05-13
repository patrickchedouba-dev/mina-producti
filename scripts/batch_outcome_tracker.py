#!/usr/bin/env python3
"""
Batch Outcome Tracker - Collecte les outcomes J+7/J+30.

Usage:
    python scripts/batch_outcome_tracker.py --days 7
    python scripts/batch_outcome_tracker.py --days 30
    
Cron recommandé:
    # J+7
    0 6 * * * cd /app && python scripts/batch_outcome_tracker.py --days 7
    # J+30
    0 6 * * * cd /app && python scripts/batch_outcome_tracker.py --days 30
"""

import os
import sys
import json
import logging
import argparse
from datetime import datetime, timedelta
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def collect_outcomes_from_crm(client_ids: list, days: int) -> dict:
    """
    Collecte les outcomes depuis le CRM.
    
    Utilise le client CRM configuré (mock ou réel selon CRM_PROVIDER).
    
    Returns:
        {client_id: {returned: bool, purchased: bool, basket_value: float}}
    """
    from backend.crm import get_crm_client
    
    crm = get_crm_client()
    logger.info(f"📡 CRM Client: {type(crm).__name__}")
    
    outcomes = crm.get_client_outcomes(client_ids, days)
    
    return outcomes


def update_decision_outcomes(decisions: list, outcomes: dict, days: int):
    """Mise à jour des outcomes dans PostgreSQL."""
    from backend.agent.outcome_logger import get_outcome_logger
    from backend.agent.regret_calculator import get_regret_calculator, OutcomeData
    
    outcome_logger = get_outcome_logger()
    regret_calc = get_regret_calculator()
    
    outcome_type = "7d" if days <= 7 else "30d"
    updated = 0
    
    for decision in decisions:
        client_id = decision.get("client_id")
        decision_id = decision.get("decision_id")
        
        if not client_id or client_id not in outcomes:
            continue
        
        outcome_raw = outcomes[client_id]
        
        # Construire OutcomeData
        outcome = OutcomeData(
            decision_id=decision_id,
            returned_7d=outcome_raw.get("returned", False) if days == 7 else False,
            returned_30d=outcome_raw.get("returned", False) if days == 30 else False,
            purchased=outcome_raw.get("purchased", False),
            basket_value=outcome_raw.get("basket_value", 0),
            satisfaction=outcome_raw.get("satisfaction"),
            cancelled=outcome_raw.get("cancelled", False),
            collected_at=datetime.now().isoformat()
        )
        
        # Update outcome
        success = outcome_logger.update_outcome(
            decision_id=decision_id,
            outcome_type=outcome_type,
            outcome_data=outcome.to_dict()
        )
        
        if success:
            # Calculer regret si on a les deux outcomes (7d ET 30d)
            if outcome_type == "30d":
                shadow_paths = json.loads(decision.get("shadow_paths", "[]"))
                regret = regret_calc.calculate_regret(decision_id, outcome, shadow_paths)
                
                # Store regret score
                try:
                    from backend.memory import get_memory_system
                    memory = get_memory_system()
                    if hasattr(memory, '_postgres') and memory._postgres:
                        memory._postgres.execute("""
                            UPDATE counterfactual_decisions
                            SET regret_score = %s
                            WHERE decision_id = %s
                        """, (regret.regret, decision_id))
                        logger.info(f"📊 Regret {decision_id}: {regret.regret:.3f} ({regret.analysis})")
                except Exception as e:
                    logger.warning(f"⚠️ Update regret: {e}")
            
            updated += 1
    
    return updated


def get_pending_decisions(days: int) -> list:
    """Récupère les décisions nécessitant un outcome."""
    try:
        from backend.memory import get_memory_system
        memory = get_memory_system()
        
        if not hasattr(memory, '_postgres') or not memory._postgres:
            logger.error("❌ PostgreSQL non disponible")
            return []
        
        # Décisions datant de `days` jours sans outcome correspondant
        outcome_column = "outcome_7d" if days <= 7 else "outcome_30d"
        
        query = f"""
            SELECT * FROM counterfactual_decisions
            WHERE {outcome_column} IS NULL
            AND timestamp < NOW() - INTERVAL '{days} days'
            AND timestamp > NOW() - INTERVAL '{days + 7} days'
            ORDER BY timestamp ASC
            LIMIT 1000
        """
        
        result = memory._postgres.fetch_all(query, ())
        return [dict(row) for row in result] if result else []
        
    except Exception as e:
        logger.error(f"❌ Fetch decisions: {e}")
        return []


def main():
    parser = argparse.ArgumentParser(description="Batch Outcome Tracker")
    parser.add_argument("--days", type=int, required=True, choices=[7, 30],
                        help="Période de suivi (7 ou 30 jours)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Mode simulation sans écriture")
    args = parser.parse_args()
    
    logger.info(f"🚀 Batch Outcome Tracker - J+{args.days}")
    logger.info("=" * 60)
    
    # 1. Récupérer décisions pending
    decisions = get_pending_decisions(args.days)
    logger.info(f"📋 Décisions à traiter: {len(decisions)}")
    
    if not decisions:
        logger.info("✅ Aucune décision à traiter")
        return
    
    # 2. Collecter client IDs
    client_ids = list(set(
        d.get("client_id") for d in decisions 
        if d.get("client_id")
    ))
    logger.info(f"👥 Clients uniques: {len(client_ids)}")
    
    if args.dry_run:
        logger.info("🔶 DRY RUN - Pas d'écriture")
        return
    
    # 3. Collecter outcomes depuis CRM
    outcomes = collect_outcomes_from_crm(client_ids, args.days)
    logger.info(f"📊 Outcomes collectés: {len(outcomes)}")
    
    # 4. Mettre à jour les décisions
    updated = update_decision_outcomes(decisions, outcomes, args.days)
    logger.info(f"✅ Décisions mises à jour: {updated}/{len(decisions)}")
    
    # 5. Résumé
    logger.info("=" * 60)
    logger.info(f"🏁 Batch terminé - {updated} outcomes enregistrés")


if __name__ == "__main__":
    main()
