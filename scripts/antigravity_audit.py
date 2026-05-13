import os
import sys

# Cibles identifiées dans le CDC v2.0 Section 6 Catégorie C
CLEANUP_TARGETS = {
    "app/config.py": ["FAQ_RESPONSES", "SEASONAL_TIPS"],
    "backend/conversation_rules.py": ["STRATEGY_OPENERS", "BINARY_QUESTIONS"]
}

def fix_taboos():
    print("🚀 ANTIGRAVITY : DÉMARRAGE DU NETTOYAGE CHIRURGICAL...\n")
    for file_path, patterns in CLEANUP_TARGETS.items():
        full_path = os.path.join(os.getcwd(), file_path)
        if not os.path.exists(full_path):
            print(f"⚠️ Fichier introuvable : {file_path}")
            continue
            
        with open(full_path, 'r') as f:
            lines = f.readlines()
            
        new_lines = []
        removed_count = 0
        skip_mode = False
        
        for line in lines:
            # Détection du début d'un bloc tabou
            if any(p in line for p in patterns):
                print(f"🔥 Suppression d'un tabou détecté dans {file_path}...")
                removed_count += 1
                continue
            new_lines.append(line)
            
        with open(full_path, 'w') as f:
            f.writelines(new_lines)
        print(f"✅ {file_path} nettoyé ({removed_count} blocs supprimés).\n")

if __name__ == "__main__":
    if "--fix-taboos" in sys.argv:
        fix_taboos()
    else:
        print("Usage: python3 antigravity_audit.py --fix-taboos")
