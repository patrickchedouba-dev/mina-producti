"""
Script de test pour vérifier le RAG sur la collection Qdrant.
Effectue des requêtes de recherche sémantique et valide les résultats.
"""

import logging
import sys
from typing import List, Optional
from dataclasses import dataclass

from .config import settings, setup_logging
from .embeddings_client import get_embeddings_client, EmbeddingsClient
from .qdrant_client import get_qdrant_client, QdrantVectorClient, SearchResult
from .collection_router import choose_collection_for_question

logger = logging.getLogger(__name__)


@dataclass
class TestQuery:
    """
    Requête de test avec résultat attendu.
    
    Attributes:
        query: Question en langage naturel
        expected_keywords: Mots-clés attendus dans les résultats
        description: Description du test
    """
    query: str
    expected_keywords: List[str]
    description: str


class RetrievalTester:
    """
    Testeur de recherche sémantique.
    
    Valide que le pipeline RAG retourne des résultats pertinents.
    """
    
    def __init__(
        self,
        qdrant_client: Optional[QdrantVectorClient] = None,
        embeddings_client: Optional[EmbeddingsClient] = None
    ):
        """
        Initialise le testeur.
        
        Args:
            qdrant_client: Client Qdrant
            embeddings_client: Client d'embeddings
        """
        self.qdrant = qdrant_client or get_qdrant_client()
        self.embeddings = embeddings_client or get_embeddings_client()
        
        logger.info("RetrievalTester initialisé")
    
    def search(
        self,
        query: str,
        limit: int = 5
    ) -> List[SearchResult]:
        """
        Effectue une recherche sémantique avec routage automatique.
        
        Args:
            query: Question en langage naturel
            limit: Nombre max de résultats
        
        Returns:
            Liste de résultats
        """
        logger.info(f"Recherche: '{query}'")
        
        # Déterminer la collection cible via le routeur
        collection = choose_collection_for_question(query)
        logger.info(f"Collection sélectionnée: {collection}")
        
        # Génération de l'embedding de la requête
        query_vector = self.embeddings.embed_text(query)
        
        # Recherche dans Qdrant avec la collection routée
        results = self.qdrant.search(
            query_vector=query_vector,
            limit=limit,
            collection_name=collection
        )
        
        return results
    
    def run_test(self, test: TestQuery) -> bool:
        """
        Exécute un test de recherche.
        
        Args:
            test: Définition du test
        
        Returns:
            True si le test passe
        """
        logger.info(f"=== TEST: {test.description} ===")
        logger.info(f"Query: {test.query}")
        logger.info(f"Keywords attendus: {test.expected_keywords}")
        
        try:
            results = self.search(test.query, limit=3)
            
            if not results:
                logger.warning("Aucun résultat retourné")
                return False
            
            # Vérification des mots-clés
            all_content = " ".join(r.content.lower() for r in results)
            found_keywords = []
            missing_keywords = []
            
            for keyword in test.expected_keywords:
                if keyword.lower() in all_content:
                    found_keywords.append(keyword)
                else:
                    missing_keywords.append(keyword)
            
            # Affichage des résultats
            logger.info(f"Résultats ({len(results)}):")
            for i, result in enumerate(results, 1):
                logger.info(
                    f"  {i}. Score: {result.score:.4f} | "
                    f"Source: {result.metadata.get('source_path', 'N/A')}"
                )
                # Aperçu du contenu (100 premiers caractères)
                preview = result.content[:100].replace("\n", " ")
                logger.info(f"     Aperçu: {preview}...")
            
            logger.info(f"Keywords trouvés: {found_keywords}")
            if missing_keywords:
                logger.warning(f"Keywords manquants: {missing_keywords}")
            
            # Le test passe si au moins 50% des keywords sont trouvés
            success_rate = len(found_keywords) / len(test.expected_keywords)
            passed = success_rate >= 0.5
            
            if passed:
                logger.info(f"✅ TEST RÉUSSI ({success_rate*100:.0f}% keywords)")
            else:
                logger.error(f"❌ TEST ÉCHOUÉ ({success_rate*100:.0f}% keywords)")
            
            return passed
            
        except Exception as e:
            logger.error(f"❌ TEST ERREUR: {e}")
            return False
    
    def run_all_tests(self) -> dict:
        """
        Exécute tous les tests prédéfinis.
        
        Returns:
            Dictionnaire avec les résultats
        """
        # Tests prédéfinis pour Body Minute
        tests = [
            TestQuery(
                query="Comment réaliser un soin du visage ?",
                expected_keywords=["soin", "visage", "peau", "nettoyage"],
                description="Recherche soin visage"
            ),
            TestQuery(
                query="Quels sont les protocoles d'épilation ?",
                expected_keywords=["épilation", "cire", "peau"],
                description="Recherche épilation"
            ),
            TestQuery(
                query="Tarifs et abonnements disponibles",
                expected_keywords=["tarif", "prix", "abonnement", "forfait"],
                description="Recherche tarifs"
            ),
            TestQuery(
                query="Règles d'hygiène en institut",
                expected_keywords=["hygiène", "désinfection", "nettoyage"],
                description="Recherche hygiène"
            ),
            TestQuery(
                query="Formation des esthéticiennes",
                expected_keywords=["formation", "esthéticienne", "technique"],
                description="Recherche formation"
            ),
        ]
        
        logger.info("=" * 60)
        logger.info("DÉMARRAGE DES TESTS DE RETRIEVAL")
        logger.info("=" * 60)
        
        results = {
            "total": len(tests),
            "passed": 0,
            "failed": 0,
            "details": []
        }
        
        for test in tests:
            passed = self.run_test(test)
            if passed:
                results["passed"] += 1
            else:
                results["failed"] += 1
            results["details"].append({
                "description": test.description,
                "passed": passed
            })
            logger.info("")  # Ligne vide entre les tests
        
        logger.info("=" * 60)
        logger.info("RÉSUMÉ DES TESTS")
        logger.info(f"Total: {results['total']}")
        logger.info(f"Réussis: {results['passed']}")
        logger.info(f"Échoués: {results['failed']}")
        logger.info(f"Taux de réussite: {results['passed']/results['total']*100:.0f}%")
        logger.info("=" * 60)
        
        return results
    
    def interactive_search(self):
        """
        Mode interactif pour tester des requêtes.
        """
        logger.info("Mode interactif - tapez 'quit' pour sortir")
        
        while True:
            try:
                query = input("\n🔍 Votre question: ").strip()
                
                if query.lower() in ["quit", "exit", "q"]:
                    break
                
                if not query:
                    continue
                
                results = self.search(query, limit=5)
                
                if not results:
                    print("Aucun résultat trouvé.")
                    continue
                
                print(f"\n📄 {len(results)} résultats:\n")
                for i, result in enumerate(results, 1):
                    print(f"--- Résultat {i} (score: {result.score:.4f}) ---")
                    print(f"Source: {result.metadata.get('source_path', 'N/A')}")
                    print(f"Chunk: {result.metadata.get('chunk_index', 'N/A')}")
                    print(f"\n{result.content[:500]}...\n")
                    
            except KeyboardInterrupt:
                break
            except Exception as e:
                logger.error(f"Erreur: {e}")
        
        print("\nAu revoir!")


def main():
    """Point d'entrée du script de test."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Tests de retrieval Mina"
    )
    parser.add_argument(
        "--interactive", "-i",
        action="store_true",
        help="Mode interactif"
    )
    parser.add_argument(
        "--query", "-q",
        type=str,
        default=None,
        help="Requête unique à tester"
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Mode debug"
    )
    
    args = parser.parse_args()
    
    # Configuration du logging
    log_level = "DEBUG" if args.debug else "INFO"
    setup_logging(log_level)
    
    tester = RetrievalTester()
    
    # Test de connexion
    try:
        info = tester.qdrant.get_collection_info()
        logger.info(f"Collection: {info['name']}, Vecteurs: {info['vectors_count']}")
    except Exception as e:
        logger.error(f"Impossible de se connecter à Qdrant: {e}")
        sys.exit(1)
    
    if args.interactive:
        tester.interactive_search()
    elif args.query:
        results = tester.search(args.query)
        for r in results:
            print(f"[{r.score:.4f}] {r.content[:200]}...")
    else:
        results = tester.run_all_tests()
        sys.exit(0 if results["failed"] == 0 else 1)


if __name__ == "__main__":
    main()
