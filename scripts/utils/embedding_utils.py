#!/usr/bin/env python3
"""
Utilitaires centralisés pour les embeddings.
Mode 1: Google Generative AI (GOOGLE_API_KEY) - GRATUIT
Mode 2: Vertex AI (GCP_PROJECT_ID) - Cloud payant
Mode 3: Local SentenceTransformers - Fallback (ATTENTION: 384D != 768D)
"""

import os
import sys
from typing import List
from functools import lru_cache
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
load_dotenv()

_embedding_model = None
_model_type = None


def get_embedding_model():
    """
    Retourne le modèle d'embedding.
    Priorité: 1. Google Generative AI  2. Vertex AI  3. Local
    """
    global _embedding_model, _model_type
    
    if _embedding_model is not None:
        return _embedding_model
    
    google_api_key = os.getenv("GOOGLE_API_KEY")
    gcp_project_id = os.getenv("GCP_PROJECT_ID")
    
    # === Option 1: Google Generative AI (gratuit avec GOOGLE_API_KEY) ===
    if google_api_key and not gcp_project_id:
        try:
            from google import genai
            genai.configure(api_key=google_api_key)
            _model_type = "google_genai"
            _embedding_model = "google_genai"
            print("✅ MODE: Google Generative AI (embedding-001, 768D)")
            return _embedding_model
        except Exception as e:
            print(f"⚠️ Erreur Google GenAI: {e}")
    
    # === Option 2: Vertex AI (nécessite GCP_PROJECT_ID) ===
    if gcp_project_id:
        try:
            import vertexai
            from vertexai.language_models import TextEmbeddingModel
            location = os.getenv("GCP_LOCATION", "europe-west1")
            vertexai.init(project=gcp_project_id, location=location)
            _embedding_model = TextEmbeddingModel.from_pretrained("text-embedding-004")
            _model_type = "vertex"
            print("☁️ MODE: Vertex AI (768D)")
            return _embedding_model
        except Exception as e:
            print(f"⚠️ Erreur Vertex AI: {e}")
    
    # === Option 3: Local SentenceTransformers (ATTENTION: 384D) ===
    try:
        from sentence_transformers import SentenceTransformer
        _embedding_model = SentenceTransformer("all-MiniLM-L6-v2")
        _model_type = "local"
        print("⚠️ MODE LOCAL: 384D - INCOMPATIBLE avec index 768D!")
        return _embedding_model
    except ImportError:
        raise RuntimeError("Aucun modèle d'embedding disponible. Configure GOOGLE_API_KEY ou installe sentence-transformers.")


def get_embedding(text: str) -> List[float]:
    """Génère l'embedding pour un texte."""
    global _model_type
    
    model = get_embedding_model()
    
    if _model_type == "google_genai":
        from google import genai
        result = genai.embed_content(
            model="models/embedding-001",
            content=text,
            task_type="retrieval_document"
        )
        return result['embedding']
    
    elif _model_type == "vertex":
        embeddings = model.get_embeddings([text])
        return embeddings[0].values
    
    elif _model_type == "local":
        return model.encode([text])[0].tolist()
    
    raise RuntimeError("Modèle non initialisé")


@lru_cache(maxsize=256)
def get_embedding_cached(text: str) -> tuple:
    """Version avec cache LRU."""
    return tuple(get_embedding(text))


def embed_batch(texts: List[str], batch_size: int = 100) -> List[List[float]]:
    """Génère les embeddings par batch."""
    global _model_type
    
    model = get_embedding_model()
    all_embeddings = []
    
    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]
        
        if _model_type == "google_genai":
            from google import genai
            for text in batch:
                result = genai.embed_content(
                    model="models/embedding-001",
                    content=text,
                    task_type="retrieval_document"
                )
                all_embeddings.append(result['embedding'])
        
        elif _model_type == "vertex":
            embeddings = model.get_embeddings(batch)
            all_embeddings.extend([e.values for e in embeddings])
        
        elif _model_type == "local":
            vectors = model.encode(batch)
            all_embeddings.extend([v.tolist() for v in vectors])
    
    return all_embeddings


if __name__ == "__main__":
    print("=== TEST EMBEDDINGS ===")
    vec = get_embedding("Test Body Minute")
    print(f"Dimensions: {len(vec)}")
    print(f"Type modèle: {_model_type}")
