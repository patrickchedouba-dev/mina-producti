"""
Point d'entrée du service autonome MINA L6.

Usage:
    python -m backend.autonomy.run
"""

import logging
import os
import signal
import sys

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("mina.autonomy")


def main():
    """Démarre la boucle autonome MINA."""
    db_url = os.getenv("DATABASE_URL", os.getenv("POSTGRES_URL", "sqlite:///mina_jobs.db"))
    logger.info("🔧 DATABASE_URL = %s", db_url[:40] + "..." if len(db_url) > 40 else db_url)

    from .scheduler import AutonomyScheduler

    scheduler = AutonomyScheduler(database_url=db_url)
    scheduler.register_all()
    scheduler.start()

    # Arrêt propre sur SIGINT / SIGTERM
    def shutdown(signum, frame):
        logger.info("Signal %s reçu — arrêt en cours…", signum)
        scheduler.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    logger.info("✅ Service autonome MINA L6 actif — Ctrl+C pour arrêter")

    # Boucle infinie
    try:
        signal.pause()
    except AttributeError:
        # Windows fallback
        import time
        while True:
            time.sleep(60)


if __name__ == "__main__":
    main()
