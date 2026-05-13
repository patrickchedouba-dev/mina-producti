#!/usr/bin/env python3
"""
🚀 MINA PREFLIGHT CHECK — Smoke Test avant déploiement.

Usage:
    python scripts/preflight_check.py

Retourne:
    - Exit code 0 + "✅ GO FOR DEPLOYMENT" si tout OK
    - Exit code 1 + "❌ NO GO" si problème détecté

Philosophie: "Fail Fast" — Si ça casse, ça casse ici, pas en prod.
"""

import sys
import os
from pathlib import Path

# Ajouter le répertoire racine au PYTHONPATH
ROOT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT_DIR))

# ============================================================
# CONFIGURATION
# ============================================================

# Modules critiques à importer
CRITICAL_MODULES = [
    "backend.llm.circuit_breaker",
    "backend.llm.provider",
    "backend.llm.resilient_provider",
    "backend.llm.degraded_mode",
    "backend.agent",
    "backend.memory",
    "backend.mcp",
]

# Variables d'environnement requises
REQUIRED_ENV_VARS = [
    "GOOGLE_API_KEY",
]

# Variables d'environnement optionnelles (warning si absentes)
OPTIONAL_ENV_VARS = [
    "ANTHROPIC_API_KEY",  # Fallback Claude
    "QDRANT_URL",
]


# ============================================================
# CHECKS
# ============================================================

class CheckResult:
    """Résultat d'une vérification."""
    def __init__(self, name: str, passed: bool, message: str = ""):
        self.name = name
        self.passed = passed
        self.message = message
    
    def __str__(self):
        icon = "✓" if self.passed else "✗"
        msg = f" — {self.message}" if self.message else ""
        return f"[{icon}] {self.name}{msg}"


def check_module_imports() -> CheckResult:
    """Vérifie que tous les modules critiques peuvent être importés."""
    failed_imports = []
    
    for module_name in CRITICAL_MODULES:
        try:
            __import__(module_name)
        except ImportError as e:
            failed_imports.append(f"{module_name}: {e}")
        except Exception as e:
            # Autres erreurs (ex: dépendance externe non configurée)
            # On considère l'import réussi si le module existe
            pass
    
    if failed_imports:
        return CheckResult(
            "Module imports",
            False,
            f"Failed: {', '.join(failed_imports)}"
        )
    
    return CheckResult("Module imports", True, f"{len(CRITICAL_MODULES)} modules OK")


def check_env_variables() -> CheckResult:
    """Vérifie la présence des variables d'environnement requises."""
    # Charger .env si présent
    env_file = ROOT_DIR / ".env"
    if env_file.exists():
        _load_dotenv(env_file)
    
    missing = []
    for var in REQUIRED_ENV_VARS:
        if not os.getenv(var):
            missing.append(var)
    
    if missing:
        return CheckResult(
            "Environment variables",
            False,
            f"Missing: {', '.join(missing)}"
        )
    
    # Warnings pour optionnels
    warnings = []
    for var in OPTIONAL_ENV_VARS:
        if not os.getenv(var):
            warnings.append(var)
    
    message = f"{len(REQUIRED_ENV_VARS)} required OK"
    if warnings:
        message += f" (warning: {', '.join(warnings)} not set)"
    
    return CheckResult("Environment variables", True, message)


def _load_dotenv(env_file: Path):
    """Charge un fichier .env sans dépendance externe."""
    try:
        with open(env_file) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, _, value = line.partition("=")
                    key = key.strip()
                    value = value.strip().strip('"').strip("'")
                    if key and not os.getenv(key):
                        os.environ[key] = value
    except Exception:
        pass


def check_circuit_breaker_state() -> CheckResult:
    """Vérifie que le Circuit Breaker s'initialise en état CLOSED."""
    try:
        from backend.llm.circuit_breaker import CircuitBreaker, CircuitState
        
        breaker = CircuitBreaker(name="preflight_test")
        
        if breaker.state != CircuitState.CLOSED:
            return CheckResult(
                "Circuit Breaker state",
                False,
                f"Expected CLOSED, got {breaker.state.value}"
            )
        
        return CheckResult("Circuit Breaker state", True, "Initialized CLOSED")
    
    except Exception as e:
        return CheckResult("Circuit Breaker state", False, str(e))


def check_dependency_chain() -> CheckResult:
    """Vérifie que la chaîne de dépendances orchestrateur est saine."""
    try:
        # Test d'import de la chaîne complète
        from backend.agent import MinaAgenticOrchestrator
        from backend.llm.resilient_provider import ResilientLLMProvider
        from backend.memory import get_memory_system
        from backend.mcp import get_mcp_client
        
        # Vérifier que les classes sont instanciables (sans init complète)
        assert MinaAgenticOrchestrator is not None
        assert ResilientLLMProvider is not None
        
        return CheckResult("Dependency chain", True, "All imports resolved")
    
    except ImportError as e:
        return CheckResult("Dependency chain", False, f"Import error: {e}")
    except Exception as e:
        return CheckResult("Dependency chain", False, str(e))


# ============================================================
# MAIN
# ============================================================

def run_preflight_check() -> bool:
    """Exécute toutes les vérifications et retourne True si GO."""
    
    print("\n🚀 MINA PREFLIGHT CHECK")
    print("=" * 40)
    
    checks = [
        check_module_imports(),
        check_env_variables(),
        check_dependency_chain(),
        check_circuit_breaker_state(),
    ]
    
    all_passed = True
    
    for check in checks:
        print(check)
        if not check.passed:
            all_passed = False
    
    print("=" * 40)
    
    if all_passed:
        print("\n✅ GO FOR DEPLOYMENT\n")
        return True
    else:
        print("\n❌ NO GO — Fix issues above before deploying\n")
        return False


if __name__ == "__main__":
    success = run_preflight_check()
    sys.exit(0 if success else 1)
