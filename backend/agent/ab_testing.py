"""
A/B Testing Framework - Validation des shadow paths en conditions réelles.

Permet de tester les alternatives contrefactuelles sur un % de trafic.
"""

import os
import json
import logging
import hashlib
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


class ExperimentStatus(Enum):
    """Statut d'une expérience A/B."""
    DRAFT = "draft"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


@dataclass
class Variant:
    """Variante d'un test A/B."""
    name: str
    description: str
    path_type: str  # "real", "cheaper", "premium", "minimal", "safe"
    traffic_percent: float  # 0-100
    parameters: Dict = field(default_factory=dict)
    conversions: int = 0
    impressions: int = 0
    
    @property
    def conversion_rate(self) -> float:
        return self.conversions / self.impressions if self.impressions > 0 else 0.0
    
    def to_dict(self) -> Dict:
        return {
            "name": self.name,
            "description": self.description,
            "path_type": self.path_type,
            "traffic_percent": self.traffic_percent,
            "parameters": self.parameters,
            "conversions": self.conversions,
            "impressions": self.impressions,
            "conversion_rate": round(self.conversion_rate * 100, 2)
        }


@dataclass
class Experiment:
    """Expérience A/B complète."""
    experiment_id: str
    name: str
    description: str
    institut_id: str
    status: ExperimentStatus
    variants: List[Variant]
    start_date: str
    end_date: Optional[str] = None
    target_sample_size: int = 1000
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def assign_variant(self, session_id: str) -> Variant:
        """Assigne une variante à une session de façon déterministe."""
        # Hash pour assignation stable
        hash_input = f"{self.experiment_id}:{session_id}"
        hash_value = int(hashlib.md5(hash_input.encode()).hexdigest(), 16)
        bucket = hash_value % 100
        
        cumulative = 0.0
        for variant in self.variants:
            cumulative += variant.traffic_percent
            if bucket < cumulative:
                return variant
        
        return self.variants[0]  # Fallback
    
    @property
    def total_impressions(self) -> int:
        return sum(v.impressions for v in self.variants)
    
    @property
    def is_significant(self) -> bool:
        """Check si résultats statistiquement significatifs (simplifié)."""
        return self.total_impressions >= self.target_sample_size
    
    def get_winner(self) -> Optional[Variant]:
        """Retourne la variante gagnante si significant."""
        if not self.is_significant:
            return None
        
        return max(self.variants, key=lambda v: v.conversion_rate)
    
    def to_dict(self) -> Dict:
        winner = self.get_winner()
        return {
            "experiment_id": self.experiment_id,
            "name": self.name,
            "description": self.description,
            "institut_id": self.institut_id,
            "status": self.status.value,
            "variants": [v.to_dict() for v in self.variants],
            "start_date": self.start_date,
            "end_date": self.end_date,
            "total_impressions": self.total_impressions,
            "is_significant": self.is_significant,
            "winner": winner.name if winner else None,
            "created_at": self.created_at
        }


class ABTestingManager:
    """
    Gestionnaire des expériences A/B.
    
    Usage:
    ```python
    manager = get_ab_manager()
    
    # Créer expérience
    exp = manager.create_experiment(
        name="Test Budget First",
        institut_id="laurence_01",
        variants=[
            Variant("control", "Real path", "real", 50),
            Variant("treatment", "Cheaper path", "cheaper", 50)
        ]
    )
    
    # Assigner variant
    variant = manager.assign_variant("laurence_01", session_id)
    
    # Track conversion
    manager.track_conversion(exp.experiment_id, variant.name)
    ```
    """
    
    def __init__(self):
        self._experiments: Dict[str, Experiment] = {}
        self._postgres = None
    
    def _ensure_db(self):
        if self._postgres:
            return
        
        try:
            from backend.memory import get_memory_system
            memory = get_memory_system()
            if hasattr(memory, '_postgres'):
                self._postgres = memory._postgres
                self._ensure_tables()
        except:
            pass
    
    def _ensure_tables(self):
        """Crée les tables si nécessaire."""
        if not self._postgres:
            return
        
        try:
            self._postgres.execute("""
                CREATE TABLE IF NOT EXISTS ab_experiments (
                    id SERIAL PRIMARY KEY,
                    experiment_id VARCHAR(64) UNIQUE NOT NULL,
                    name VARCHAR(256),
                    description TEXT,
                    institut_id VARCHAR(64),
                    status VARCHAR(32),
                    variants JSONB,
                    start_date TIMESTAMP,
                    end_date TIMESTAMP,
                    target_sample_size INT,
                    created_at TIMESTAMP DEFAULT NOW()
                );
                
                CREATE TABLE IF NOT EXISTS ab_assignments (
                    id SERIAL PRIMARY KEY,
                    experiment_id VARCHAR(64),
                    session_id VARCHAR(128),
                    variant_name VARCHAR(64),
                    assigned_at TIMESTAMP DEFAULT NOW(),
                    converted BOOLEAN DEFAULT FALSE,
                    converted_at TIMESTAMP
                );
                
                CREATE INDEX IF NOT EXISTS idx_ab_exp ON ab_assignments(experiment_id);
                CREATE INDEX IF NOT EXISTS idx_ab_session ON ab_assignments(session_id);
            """)
        except Exception as e:
            logger.warning(f"⚠️ Create AB tables: {e}")
    
    def create_experiment(
        self,
        name: str,
        institut_id: str,
        variants: List[Variant],
        description: str = "",
        target_sample_size: int = 1000
    ) -> Experiment:
        """Crée une nouvelle expérience A/B."""
        import uuid
        
        experiment_id = f"exp_{uuid.uuid4().hex[:12]}"
        
        # Valider % traffic
        total_traffic = sum(v.traffic_percent for v in variants)
        if abs(total_traffic - 100) > 0.1:
            raise ValueError(f"Traffic percentages must sum to 100, got {total_traffic}")
        
        experiment = Experiment(
            experiment_id=experiment_id,
            name=name,
            description=description,
            institut_id=institut_id,
            status=ExperimentStatus.RUNNING,
            variants=variants,
            start_date=datetime.now().isoformat(),
            target_sample_size=target_sample_size
        )
        
        self._experiments[experiment_id] = experiment
        self._save_experiment(experiment)
        
        logger.info(f"🧪 Created experiment: {name} ({experiment_id})")
        return experiment
    
    def _save_experiment(self, exp: Experiment):
        """Sauvegarde en base."""
        self._ensure_db()
        
        if not self._postgres:
            return
        
        try:
            self._postgres.execute("""
                INSERT INTO ab_experiments 
                (experiment_id, name, description, institut_id, status, variants, start_date, target_sample_size)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (experiment_id) DO UPDATE SET
                    status = EXCLUDED.status,
                    variants = EXCLUDED.variants,
                    end_date = EXCLUDED.end_date
            """, (
                exp.experiment_id,
                exp.name,
                exp.description,
                exp.institut_id,
                exp.status.value,
                json.dumps([v.to_dict() for v in exp.variants]),
                exp.start_date,
                exp.target_sample_size
            ))
        except Exception as e:
            logger.warning(f"⚠️ Save experiment: {e}")
    
    def get_active_experiment(self, institut_id: str) -> Optional[Experiment]:
        """Récupère l'expérience active pour un institut."""
        for exp in self._experiments.values():
            if exp.institut_id == institut_id and exp.status == ExperimentStatus.RUNNING:
                return exp
        
        # Chercher en base
        self._ensure_db()
        if self._postgres:
            try:
                result = self._postgres.fetch_one("""
                    SELECT * FROM ab_experiments
                    WHERE institut_id = %s AND status = 'running'
                    ORDER BY created_at DESC LIMIT 1
                """, (institut_id,))
                
                if result:
                    return self._load_experiment_from_row(result)
            except:
                pass
        
        return None
    
    def _load_experiment_from_row(self, row: Dict) -> Experiment:
        """Charge une expérience depuis une row DB."""
        variants_data = json.loads(row.get("variants", "[]"))
        variants = [
            Variant(
                name=v["name"],
                description=v["description"],
                path_type=v["path_type"],
                traffic_percent=v["traffic_percent"],
                parameters=v.get("parameters", {}),
                conversions=v.get("conversions", 0),
                impressions=v.get("impressions", 0)
            )
            for v in variants_data
        ]
        
        return Experiment(
            experiment_id=row["experiment_id"],
            name=row["name"],
            description=row.get("description", ""),
            institut_id=row["institut_id"],
            status=ExperimentStatus(row["status"]),
            variants=variants,
            start_date=str(row["start_date"]),
            end_date=str(row["end_date"]) if row.get("end_date") else None,
            target_sample_size=row.get("target_sample_size", 1000),
            created_at=str(row["created_at"])
        )
    
    def assign_variant(self, institut_id: str, session_id: str) -> Optional[Tuple[Experiment, Variant]]:
        """
        Assigne une variante à une session.
        
        Returns:
            (Experiment, Variant) si une expérience est active, None sinon
        """
        experiment = self.get_active_experiment(institut_id)
        
        if not experiment:
            return None
        
        variant = experiment.assign_variant(session_id)
        variant.impressions += 1
        
        # Log assignment
        self._log_assignment(experiment.experiment_id, session_id, variant.name)
        
        logger.debug(f"🧪 Assigned {session_id} → {variant.name}")
        return (experiment, variant)
    
    def _log_assignment(self, experiment_id: str, session_id: str, variant_name: str):
        """Log l'assignation en base."""
        self._ensure_db()
        
        if not self._postgres:
            return
        
        try:
            self._postgres.execute("""
                INSERT INTO ab_assignments (experiment_id, session_id, variant_name)
                VALUES (%s, %s, %s)
                ON CONFLICT DO NOTHING
            """, (experiment_id, session_id, variant_name))
        except:
            pass
    
    def track_conversion(self, experiment_id: str, session_id: str) -> bool:
        """
        Track une conversion pour une session.
        
        Returns:
            True si conversion enregistrée
        """
        if experiment_id in self._experiments:
            experiment = self._experiments[experiment_id]
            
            # Trouver variant assigné
            variant = experiment.assign_variant(session_id)
            variant.conversions += 1
            self._save_experiment(experiment)
        
        # Log en base
        self._ensure_db()
        if self._postgres:
            try:
                self._postgres.execute("""
                    UPDATE ab_assignments
                    SET converted = TRUE, converted_at = NOW()
                    WHERE experiment_id = %s AND session_id = %s
                """, (experiment_id, session_id))
                return True
            except:
                pass
        
        return False
    
    def get_experiment_results(self, experiment_id: str) -> Dict:
        """Récupère les résultats d'une expérience."""
        experiment = self._experiments.get(experiment_id)
        
        if not experiment:
            return {"error": "Experiment not found"}
        
        results = experiment.to_dict()
        
        # Ajouter analyse
        if experiment.is_significant:
            winner = experiment.get_winner()
            if winner:
                results["recommendation"] = f"Déployer '{winner.name}' ({winner.path_type})"
                results["improvement"] = self._calculate_improvement(experiment.variants)
        
        return results
    
    def _calculate_improvement(self, variants: List[Variant]) -> Optional[float]:
        """Calcule l'amélioration relative."""
        control = next((v for v in variants if v.path_type == "real"), None)
        treatment = max(
            (v for v in variants if v.path_type != "real"),
            key=lambda v: v.conversion_rate,
            default=None
        )
        
        if control and treatment and control.conversion_rate > 0:
            improvement = (treatment.conversion_rate - control.conversion_rate) / control.conversion_rate * 100
            return round(improvement, 2)
        
        return None
    
    def complete_experiment(self, experiment_id: str) -> Dict:
        """Marque une expérience comme terminée."""
        if experiment_id in self._experiments:
            experiment = self._experiments[experiment_id]
            experiment.status = ExperimentStatus.COMPLETED
            experiment.end_date = datetime.now().isoformat()
            self._save_experiment(experiment)
            
            return self.get_experiment_results(experiment_id)
        
        return {"error": "Experiment not found"}


# Singleton
_ab_manager: Optional[ABTestingManager] = None


def get_ab_manager() -> ABTestingManager:
    global _ab_manager
    if _ab_manager is None:
        _ab_manager = ABTestingManager()
    return _ab_manager
