#!/usr/bin/env python3
"""
Share App - Tunnel public pour partager Mina Body Touch.

Ce script ouvre un tunnel ngrok vers localhost:8501 pour permettre
à des testeurs distants d'accéder à l'application Streamlit.

Usage:
    1. Lancez d'abord Streamlit: streamlit run scripts/app_chatbot.py
    2. Dans un autre terminal: python scripts/share_app.py
    3. Partagez l'URL affichée avec votre testeuse

Note: Vous devez avoir un compte ngrok gratuit pour les sessions longues.
      https://ngrok.com - créez un compte et récupérez votre authtoken.
"""

import sys
import time

def main():
    try:
        from pyngrok import ngrok, conf
    except ImportError:
        print("❌ pyngrok n'est pas installé.")
        print("   Installez-le avec: pip install pyngrok")
        sys.exit(1)
    
    print("=" * 60)
    print("🚀 MINA BODY TOUCH - PARTAGE PUBLIC")
    print("=" * 60)
    
    # Port Streamlit par défaut
    port = 8501
    
    print(f"\n📡 Ouverture du tunnel vers localhost:{port}...")
    
    try:
        # Ouvrir le tunnel HTTP
        public_url = ngrok.connect(port, "http")
        
        print("\n" + "=" * 60)
        print("✅ TUNNEL ACTIF - PARTAGEZ CETTE URL:")
        print("=" * 60)
        print(f"\n   🔗 {public_url}")
        print(f"\n   📱 Votre testeuse peut scanner ce lien sur son mobile")
        print("=" * 60)
        
        print("\n⚠️  Assurez-vous que Streamlit tourne dans un autre terminal:")
        print("    streamlit run scripts/app_chatbot.py")
        
        print("\n🛑 Appuyez sur Ctrl+C pour fermer le tunnel")
        print("-" * 60)
        
        # Garder le tunnel ouvert
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\n\n🔒 Fermeture du tunnel...")
        ngrok.disconnect(public_url)
        ngrok.kill()
        print("✅ Tunnel fermé. À bientôt!")
        
    except Exception as e:
        print(f"\n❌ Erreur: {e}")
        print("\n💡 Si c'est une erreur d'authtoken, configurez-le:")
        print("   1. Créez un compte gratuit sur https://ngrok.com")
        print("   2. Copiez votre authtoken depuis le dashboard")
        print("   3. Lancez: ngrok config add-authtoken VOTRE_TOKEN")
        sys.exit(1)


if __name__ == "__main__":
    main()
