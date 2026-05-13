#!/usr/bin/env python3
"""
MINA Alert Manager - Système d'Alertes SMS/Email

Gère l'envoi d'alertes via Twilio (SMS) et SMTP (Email)
avec anti-spam intégré.

Usage:
    from observer.alert_manager import AlertManager
    
    manager = AlertManager()
    manager.send_alert(alert)

Auteur: Patrick Chedouba
Date: 23 décembre 2024
"""

import os
import sys
import json
import smtplib
import logging
from datetime import datetime, timedelta
from pathlib import Path
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, Optional, List, Any
from dataclasses import dataclass

# Ajouter le projet au path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from observer.mina_observer import Alert

# ============================================================================
# CONFIGURATION
# ============================================================================

CONFIG_PATH = PROJECT_ROOT / "shared" / "config" / "alert_config.json"

# Configuration par défaut (peut être overridée par config.json ou env vars)
DEFAULT_CONFIG = {
    # Twilio SMS
    "twilio_account_sid": os.getenv("TWILIO_ACCOUNT_SID", ""),
    "twilio_auth_token": os.getenv("TWILIO_AUTH_TOKEN", ""),
    "twilio_from_phone": os.getenv("TWILIO_FROM_PHONE", ""),
    "alert_phone_numbers": os.getenv("ALERT_PHONE_NUMBERS", "").split(","),
    
    # Email SMTP
    "smtp_host": os.getenv("SMTP_HOST", "smtp.gmail.com"),
    "smtp_port": int(os.getenv("SMTP_PORT", "587")),
    "smtp_user": os.getenv("SMTP_USER", ""),
    "smtp_password": os.getenv("SMTP_PASSWORD", ""),
    "alert_emails": os.getenv("ALERT_EMAILS", "").split(","),
    "email_from": os.getenv("EMAIL_FROM", "mina-observer@bodyminute.com"),
    
    # Anti-spam
    "min_interval_minutes": 10,  # 1 alerte max par 10 min par catégorie
    "daily_limit_sms": 50,       # Max 50 SMS/jour
    "daily_limit_email": 100,    # Max 100 emails/jour
    
    # Niveaux
    "sms_levels": ["critical"],           # SMS seulement pour critical
    "email_levels": ["warning", "critical"],  # Email pour warning + critical
}

# ============================================================================
# LOGGING
# ============================================================================

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(message)s'
)
logger = logging.getLogger("AlertManager")


# ============================================================================
# ALERT MANAGER
# ============================================================================

class AlertManager:
    """
    Gestionnaire d'alertes avec support SMS (Twilio) et Email (SMTP).
    
    Fonctionnalités:
    - Envoi SMS via Twilio API
    - Envoi Email via SMTP
    - Anti-spam par catégorie
    - Limite quotidienne
    - Historique des alertes envoyées
    """
    
    def __init__(self, config: Optional[Dict] = None):
        """
        Initialise l'AlertManager.
        
        Args:
            config: Configuration personnalisée (optionnel)
        """
        self.config = self._load_config(config)
        
        # État anti-spam
        self.last_alert_by_category: Dict[str, datetime] = {}
        self.daily_counts = {
            "sms": 0,
            "email": 0,
            "date": datetime.now().date()
        }
        
        # Historique
        self.sent_alerts: List[Dict] = []
        
        # Clients
        self.twilio_client = None
        self._init_twilio()
        
        logger.info("📢 AlertManager initialisé")
        self._log_config()
    
    def _load_config(self, custom_config: Optional[Dict]) -> Dict:
        """Charge la configuration depuis fichier ou défauts."""
        config = DEFAULT_CONFIG.copy()
        
        # Essayer de charger depuis fichier
        if CONFIG_PATH.exists():
            try:
                with open(CONFIG_PATH, 'r') as f:
                    file_config = json.load(f)
                    config.update(file_config)
                    logger.info(f"   Config chargée: {CONFIG_PATH}")
            except Exception as e:
                logger.warning(f"   Erreur config: {e}")
        
        # Appliquer config personnalisée si fournie
        if custom_config:
            config.update(custom_config)
        
        return config
    
    def _log_config(self):
        """Log la configuration (masquée)."""
        has_twilio = bool(self.config.get("twilio_account_sid"))
        has_smtp = bool(self.config.get("smtp_user"))
        phones = len([p for p in self.config.get("alert_phone_numbers", []) if p])
        emails = len([e for e in self.config.get("alert_emails", []) if e])
        
        logger.info(f"   Twilio: {'✅' if has_twilio else '❌'} ({phones} destinataires)")
        logger.info(f"   SMTP: {'✅' if has_smtp else '❌'} ({emails} destinataires)")
    
    def _init_twilio(self):
        """Initialise le client Twilio si configuré."""
        sid = self.config.get("twilio_account_sid")
        token = self.config.get("twilio_auth_token")
        
        if not sid or not token:
            logger.warning("   Twilio non configuré (SMS désactivés)")
            return
        
        try:
            from twilio.rest import Client
            self.twilio_client = Client(sid, token)
            logger.info("   Twilio client initialisé ✅")
        except ImportError:
            logger.warning("   Package twilio non installé")
        except Exception as e:
            logger.error(f"   Erreur Twilio: {e}")
    
    # -------------------------------------------------------------------------
    # ANTI-SPAM
    # -------------------------------------------------------------------------
    
    def _check_cooldown(self, category: str, institut_id: Optional[str]) -> bool:
        """
        Vérifie si le cooldown est respecté pour cette catégorie.
        
        Returns:
            True si l'alerte peut être envoyée
        """
        key = f"{category}_{institut_id or 'global'}"
        now = datetime.now()
        
        if key in self.last_alert_by_category:
            last_time = self.last_alert_by_category[key]
            cooldown = timedelta(minutes=self.config["min_interval_minutes"])
            if now - last_time < cooldown:
                remaining = (cooldown - (now - last_time)).seconds // 60
                logger.debug(f"   Cooldown actif ({remaining}min restantes)")
                return False
        
        self.last_alert_by_category[key] = now
        return True
    
    def _check_daily_limit(self, channel: str) -> bool:
        """
        Vérifie si la limite quotidienne est atteinte.
        
        Args:
            channel: "sms" ou "email"
            
        Returns:
            True si l'envoi est autorisé
        """
        today = datetime.now().date()
        
        # Reset compteur si nouveau jour
        if self.daily_counts["date"] != today:
            self.daily_counts = {"sms": 0, "email": 0, "date": today}
        
        limit_key = f"daily_limit_{channel}"
        if self.daily_counts[channel] >= self.config.get(limit_key, 100):
            logger.warning(f"   Limite quotidienne {channel} atteinte")
            return False
        
        return True
    
    # -------------------------------------------------------------------------
    # ENVOI SMS
    # -------------------------------------------------------------------------
    
    def send_sms(self, message: str, phone_number: Optional[str] = None) -> bool:
        """
        Envoie un SMS via Twilio.
        
        Args:
            message: Contenu du SMS (max 160 chars recommandé)
            phone_number: Numéro destination (ou tous si None)
            
        Returns:
            True si envoi réussi
        """
        if not self.twilio_client:
            logger.warning("Twilio non configuré, SMS ignoré")
            return False
        
        if not self._check_daily_limit("sms"):
            return False
        
        from_phone = self.config.get("twilio_from_phone")
        if not from_phone:
            logger.error("Numéro Twilio source non configuré")
            return False
        
        # Déterminer destinataires
        if phone_number:
            recipients = [phone_number]
        else:
            recipients = [p for p in self.config.get("alert_phone_numbers", []) if p]
        
        if not recipients:
            logger.warning("Aucun destinataire SMS configuré")
            return False
        
        # Tronquer message si trop long
        if len(message) > 160:
            message = message[:157] + "..."
        
        success = True
        for phone in recipients:
            try:
                self.twilio_client.messages.create(
                    body=message,
                    from_=from_phone,
                    to=phone
                )
                self.daily_counts["sms"] += 1
                logger.info(f"📱 SMS envoyé → {phone[-4:]}")
            except Exception as e:
                logger.error(f"Erreur SMS {phone}: {e}")
                success = False
        
        return success
    
    # -------------------------------------------------------------------------
    # ENVOI EMAIL
    # -------------------------------------------------------------------------
    
    def send_email(
        self,
        subject: str,
        body: str,
        to_address: Optional[str] = None,
        html: bool = False
    ) -> bool:
        """
        Envoie un email via SMTP.
        
        Args:
            subject: Sujet
            body: Corps du message
            to_address: Destinataire (ou tous si None)
            html: True si body est HTML
            
        Returns:
            True si envoi réussi
        """
        smtp_host = self.config.get("smtp_host")
        smtp_user = self.config.get("smtp_user")
        smtp_password = self.config.get("smtp_password")
        
        if not smtp_user or not smtp_password:
            logger.warning("SMTP non configuré, email ignoré")
            return False
        
        if not self._check_daily_limit("email"):
            return False
        
        # Destinataires
        if to_address:
            recipients = [to_address]
        else:
            recipients = [e for e in self.config.get("alert_emails", []) if e]
        
        if not recipients:
            logger.warning("Aucun destinataire email configuré")
            return False
        
        from_addr = self.config.get("email_from", smtp_user)
        
        success = True
        for to_addr in recipients:
            try:
                msg = MIMEMultipart("alternative")
                msg["Subject"] = subject
                msg["From"] = from_addr
                msg["To"] = to_addr
                
                content_type = "html" if html else "plain"
                msg.attach(MIMEText(body, content_type, "utf-8"))
                
                with smtplib.SMTP(smtp_host, self.config.get("smtp_port", 587)) as server:
                    server.starttls()
                    server.login(smtp_user, smtp_password)
                    server.sendmail(from_addr, to_addr, msg.as_string())
                
                self.daily_counts["email"] += 1
                logger.info(f"📧 Email envoyé → {to_addr}")
                
            except Exception as e:
                logger.error(f"Erreur email {to_addr}: {e}")
                success = False
        
        return success
    
    # -------------------------------------------------------------------------
    # ENVOI ALERTE (ORCHESTRATION)
    # -------------------------------------------------------------------------
    
    def send_alert(self, alert: Alert) -> Dict[str, bool]:
        """
        Envoie une alerte sur les canaux appropriés.
        
        Args:
            alert: Objet Alert à envoyer
            
        Returns:
            Dict avec résultat par canal {"sms": bool, "email": bool}
        """
        results = {"sms": False, "email": False}
        
        # Vérifier cooldown
        if not self._check_cooldown(alert.category, alert.institut_id):
            logger.info(f"   Alerte {alert.category} en cooldown, ignorée")
            return results
        
        # Préparer messages
        sms_msg = self._format_sms(alert)
        email_subject, email_body = self._format_email(alert)
        
        # SMS pour niveaux configurés
        if alert.level in self.config.get("sms_levels", ["critical"]):
            results["sms"] = self.send_sms(sms_msg)
        
        # Email pour niveaux configurés
        if alert.level in self.config.get("email_levels", ["warning", "critical"]):
            results["email"] = self.send_email(email_subject, email_body, html=True)
        
        # Historique
        self.sent_alerts.append({
            "timestamp": datetime.now().isoformat(),
            "alert": {
                "level": alert.level,
                "category": alert.category,
                "message": alert.message,
            },
            "results": results
        })
        
        return results
    
    def _format_sms(self, alert: Alert) -> str:
        """Formate une alerte pour SMS (court)."""
        level_emoji = "🔴" if alert.level == "critical" else "🟡"
        institut = f" [{alert.institut_id}]" if alert.institut_id else ""
        return f"{level_emoji} MINA{institut}: {alert.message[:120]}"
    
    def _format_email(self, alert: Alert) -> tuple:
        """Formate une alerte pour email (détaillé)."""
        level_color = "#dc3545" if alert.level == "critical" else "#ffc107"
        level_upper = alert.level.upper()
        
        subject = f"[MINA {level_upper}] {alert.category}: {alert.message[:50]}"
        
        body = f"""
        <html>
        <body style="font-family: Arial, sans-serif; padding: 20px;">
            <div style="background: {level_color}; color: white; padding: 15px; border-radius: 5px;">
                <h2 style="margin: 0;">⚠️ MINA Alert - {level_upper}</h2>
            </div>
            
            <div style="padding: 20px; background: #f8f9fa; margin-top: 10px; border-radius: 5px;">
                <p><strong>Catégorie:</strong> {alert.category}</p>
                <p><strong>Message:</strong> {alert.message}</p>
                <p><strong>Institut:</strong> {alert.institut_id or 'Global'}</p>
                <p><strong>Timestamp:</strong> {alert.timestamp.isoformat()}</p>
                {f'<p><strong>Valeur:</strong> {alert.value} (seuil: {alert.threshold})</p>' 
                 if alert.value else ''}
            </div>
            
            <p style="color: #666; font-size: 12px; margin-top: 20px;">
                Cet email a été envoyé automatiquement par MINA Observer.<br>
                Pour plus de détails, consulter le dashboard ou les logs.
            </p>
        </body>
        </html>
        """
        
        return subject, body
    
    # -------------------------------------------------------------------------
    # UTILITAIRES
    # -------------------------------------------------------------------------
    
    def get_stats(self) -> Dict[str, Any]:
        """Retourne les statistiques d'envoi."""
        return {
            "daily_sms_sent": self.daily_counts["sms"],
            "daily_email_sent": self.daily_counts["email"],
            "total_alerts_sent": len(self.sent_alerts),
            "twilio_configured": self.twilio_client is not None,
            "smtp_configured": bool(self.config.get("smtp_user")),
        }
    
    def test_connectivity(self) -> Dict[str, bool]:
        """Teste la connectivité des services."""
        results = {"twilio": False, "smtp": False}
        
        # Test Twilio
        if self.twilio_client:
            try:
                self.twilio_client.api.accounts.list(limit=1)
                results["twilio"] = True
                logger.info("✅ Twilio connecté")
            except Exception as e:
                logger.error(f"❌ Twilio: {e}")
        
        # Test SMTP
        smtp_host = self.config.get("smtp_host")
        smtp_user = self.config.get("smtp_user")
        if smtp_user:
            try:
                with smtplib.SMTP(smtp_host, self.config.get("smtp_port", 587)) as server:
                    server.starttls()
                    server.login(smtp_user, self.config.get("smtp_password", ""))
                results["smtp"] = True
                logger.info("✅ SMTP connecté")
            except Exception as e:
                logger.error(f"❌ SMTP: {e}")
        
        return results


# ============================================================================
# CLI POUR TESTS
# ============================================================================

def main():
    """Point d'entrée CLI pour tests."""
    import argparse
    
    parser = argparse.ArgumentParser(description="MINA Alert Manager")
    parser.add_argument("--test", action="store_true", help="Tester connectivité")
    parser.add_argument("--sms", type=str, help="Envoyer SMS test")
    parser.add_argument("--email", type=str, help="Envoyer email test")
    
    args = parser.parse_args()
    
    manager = AlertManager()
    
    if args.test:
        print("\n🧪 Test connectivité...")
        results = manager.test_connectivity()
        for service, ok in results.items():
            status = "✅ OK" if ok else "❌ ÉCHEC"
            print(f"   {service}: {status}")
    
    if args.sms:
        print(f"\n📱 Envoi SMS test: {args.sms}")
        manager.send_sms(args.sms)
    
    if args.email:
        print(f"\n📧 Envoi email test")
        manager.send_email(
            subject="[TEST] MINA Observer",
            body=args.email
        )
    
    print("\n📊 Stats:")
    for k, v in manager.get_stats().items():
        print(f"   {k}: {v}")


if __name__ == "__main__":
    main()
