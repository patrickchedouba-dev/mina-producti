import os
import sys
from backend.crm.crm_client import get_crm_client
from backend.memory.postgres_client import get_postgres_client

def run_test():
    print("🔍 TEST DE RECONNAISSANCE MINA V2.0\n")
    crm = get_crm_client()
    db = get_postgres_client()

    # 1. On utilise la méthode native pour insérer Patrick
    print("--- Étape 1 : Préparation de la donnée ---")
    success = db.update_client_profile(
        client_id='patrick_001',
        skin_type='Normal',
        preferences={'role': 'COMEX', 'email': 'patrick@bodyminute.fr'}
    )
    if success:
        print("✅ Profil 'Patrick' synchronisé dans 'client_profiles'.\n")

    # 2. Test de récupération via le CRM
    print("--- Étape 2 : Interrogation via la Couche 5 (CRM) ---")
    context = crm.get_client_context("patrick_001")
    
    if context and "error" not in context:
        print(f"🤖 MINA : 'Bonjour Patrick ! Ravi de vous revoir.'")
        print(f"📊 Type de peau détecté : {context.get('skin_type')}")
        print(f"⚙️ Préférences : {context.get('preferences')}")
        print("\n✅ RÉUSSITE : Le flux Couche 4 -> Couche 5 est validé.")
    else:
        print("❌ ÉCHEC : Mina ne vous a pas trouvé.")

if __name__ == "__main__":
    run_test()
