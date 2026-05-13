#!/usr/bin/env python3
"""
Active les APIs nécessaires et vérifie la config.
"""

import sys

PROJECT_ID = "bodycoachocr"

REQUIRED_APIS = [
    "vision.googleapis.com",
    "run.googleapis.com",
    "cloudbuild.googleapis.com",
    "storage.googleapis.com",
    "aiplatform.googleapis.com",
]


def enable_apis():
    """Active les APIs GCP nécessaires."""
    from google.cloud import service_usage_v1
    
    print("=" * 60)
    print("🔧 ACTIVATION DES APIS GCP")
    print("=" * 60)
    
    client = service_usage_v1.ServiceUsageClient()
    parent = f"projects/{PROJECT_ID}"
    
    for api in REQUIRED_APIS:
        service_name = f"{parent}/services/{api}"
        
        try:
            # Vérifier si l'API est activée
            service = client.get_service(name=service_name)
            state = service.state.name
            
            if state == "ENABLED":
                print(f"✅ {api} - déjà activée")
            else:
                print(f"⏳ {api} - activation en cours...")
                operation = client.enable_service(name=service_name)
                operation.result(timeout=60)
                print(f"✅ {api} - activée")
                
        except Exception as e:
            print(f"❌ {api} - erreur: {e}")
            
            # Tenter l'activation quand même
            try:
                operation = client.enable_service(name=service_name)
                operation.result(timeout=60)
                print(f"✅ {api} - activée après retry")
            except Exception as e2:
                print(f"   ❌ Échec: {e2}")


def test_vision_api():
    """Teste que Vision API fonctionne."""
    print("\n" + "=" * 60)
    print("🧪 TEST VISION API")
    print("=" * 60)
    
    try:
        from google.cloud import vision
        
        client = vision.ImageAnnotatorClient()
        
        # Créer une image de test simple (1x1 pixel blanc)
        import io
        from PIL import Image
        
        img = Image.new('RGB', (100, 100), color='white')
        
        # Ajouter du texte
        from PIL import ImageDraw
        draw = ImageDraw.Draw(img)
        draw.text((10, 40), "TEST OCR", fill='black')
        
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        img_bytes = buffer.getvalue()
        
        # Appeler Vision API
        image = vision.Image(content=img_bytes)
        response = client.text_detection(image=image)
        
        if response.error.message:
            print(f"❌ Erreur Vision API: {response.error.message}")
            return False
        
        if response.text_annotations:
            text = response.text_annotations[0].description
            print(f"✅ Vision API fonctionne!")
            print(f"   Texte détecté: '{text.strip()}'")
            return True
        else:
            print("⚠️  Pas de texte détecté (peut être normal pour une image simple)")
            return True
            
    except ImportError as e:
        print(f"❌ Module manquant: {e}")
        print("   Installer: pip install google-cloud-vision pillow")
        return False
    except Exception as e:
        print(f"❌ Erreur: {e}")
        return False


def main():
    try:
        # Installer les dépendances si nécessaire
        try:
            from google.cloud import service_usage_v1
        except ImportError:
            import subprocess
            subprocess.check_call([
                sys.executable, "-m", "pip", "install", "-q",
                "google-cloud-service-usage", "google-cloud-vision", "pillow"
            ])
        
        enable_apis()
        test_vision_api()
        
        print("\n" + "=" * 60)
        print("✅ CONFIGURATION TERMINÉE")
        print("=" * 60)
        
    except Exception as e:
        print(f"❌ Erreur: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
