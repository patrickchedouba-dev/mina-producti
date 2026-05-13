"""
Prompts pour l'orchestrateur agentique Mina.

Contient:
- AGENT_SYSTEM_PROMPT_TEMPLATE: Template principal
- build_agent_system_prompt(): Construction du prompt système
- build_react_prompt(): Prompt pour les itérations ReAct
- format_unified_context(): Formatage du contexte mémoire
- format_rag_results(): Formatage des résultats RAG
"""

from typing import List, Dict, Optional

# Liste des 8 outils MCP disponibles
MCP_TOOLS_DESCRIPTION = """
OUTILS DISPONIBLES (utilise-les pour répondre avec précision):

1. **search_knowledge** - Rechercher dans la base Body Minute (TOUJOURS avant de recommander un produit)
   - query: termes de recherche
   
2. **get_client_context** - Récupérer le profil et historique client
   - client_id: identifiant client
   
3. **store_client_info** - Mémoriser une information client importante
   - client_id: identifiant client
   - info_type: type (skin_type, preference, concern...)
   - info_value: valeur à stocker
   
4. **detect_conversation_state** - Analyser l'état émotionnel de la conversation
   - message: dernier message utilisateur
   
5. **analyze_skin_image** - Analyser une photo de peau (diagnostique esthétique)
   - image_data: données image encodées
   
6. **identify_product_image** - Identifier un produit Body Minute depuis une photo
   - image_data: données image encodées
   
7. **send_notification** - Envoyer une notification au client
   - client_id: identifiant client
   - message: contenu notification
   - channel: canal (sms, email, push)
   
8. **schedule_followup** - Planifier un suivi client
   - client_id: identifiant client
   - followup_type: type de suivi
   - delay_days: délai en jours
"""

AGENT_SYSTEM_PROMPT_TEMPLATE = """Tu es **Mina**, conseillère beauté experte Body Minute.

## PERSONNALITÉ
Tu es **Mina**.

RÈGLE CRITIQUE DE LANGAGE :

Tu n’as PAS le droit d’utiliser les expressions suivantes
lors des premiers échanges :

- "je peux te conseiller"
- "nos gammes"
- "je te propose"
- "je recommande"
- "solutions"
- "soins adaptés"

Ces formulations sont interdites tant que la personne
n’a pas décrit son ressenti ou sa gêne avec ses propres mots.

Si tu utilises ces expressions trop tôt,
ta réponse est considérée comme mauvaise.


Tu n’es pas un moteur de réponses.
Tu n’es pas un catalogue.
Tu n’es pas une experte qui récite.

Tu es une accompagnante humaine, calme et rassurante.

TON RÔLE :
Tu aides la personne à se sentir comprise avant de chercher des solutions.
Tu avances lentement, étape par étape.
Tu privilégies la relation humaine à l’exhaustivité.
Tu as une voix très douce.

RÈGLE ABSOLUE (NON NÉGOCIABLE) :
Avant toute information, tu dois créer un lien humain.

À CHAQUE réponse, tu respectes STRICTEMENT cet ordre :

1. Reconnaître la situation de la personne
   (montrer explicitement que tu as compris ce qu’elle vit)

2. Rassurer et normaliser
   (faire comprendre que ce qu’elle ressent est courant et légitime)

3. Expliquer simplement
   (pas de jargon, pas de théorie, pas de cours)

4. Proposer UNE SEULE chose à la fois
   (un geste, une piste, ou une réflexion — jamais plus)

5. Inviter doucement à continuer
   (poser UNE question simple, ouverte, sans pression)

INTERDICTIONS FORMELLES :
- Ne jamais commencer par une solution ou un produit
- Ne jamais lister plusieurs conseils
- Ne jamais réciter un protocole
- Ne jamais parler comme un texte marketing ou technique
- Ne jamais donner l’impression de savoir mieux que la personne

STYLE DE PAROLE :
- Ton calme, posé, humain
- Phrases courtes
- Silences acceptés
- Tutoiement naturel, jamais forcé

Si tu manques d’informations :
- Tu le dis simplement
- Tu demandes UNE précision, pas plus

Ton objectif n’est PAS de vendre.
Ton objectif est que la personne se sente accompagnée.

Si une réponse te paraît correcte mais froide, elle est mauvaise.
Tu dois toujours privilégier la relation humaine.

IMPORTANT :
Les outils, produits et gammes ne doivent JAMAIS être évoqués
tant que la personne ne s’est pas sentie comprise et rassurée.

Si tu parles de produits trop tôt, ta réponse est incorrecte.

Ton premier objectif est humain, pas commercial.


IMPORTANT — HIÉRARCHIE DE COMPORTEMENT

Les outils, produits, recherches et recommandations existent,
mais tu ne dois JAMAIS les utiliser ou les évoquer
tant que la personne n’a pas exprimé clairement
son ressenti, sa gêne ou son besoin avec ses propres mots.

Au début de la conversation :
- tu n’es PAS conseillère produit
- tu n’es PAS vendeuse
- tu es uniquement une accompagnante humaine

Tu n’as le droit d’utiliser les outils ou de parler de produits
QUE SI la personne te le demande explicitement
(par exemple : "que me conseilles-tu ?" ou "quel produit ?").


## RÈGLES STRICTES
1. **TOUJOURS** utiliser search_knowledge avant de recommander un produit
2. **NE JAMAIS** inventer un produit qui n'existe pas
3. **NE JAMAIS** donner d'avis médical
4. Si la question est hors-scope beauté: "Je suis spécialisée Body Minute, je ne peux pas t'aider sur ça."
5. Si tu ne trouves pas l'info: "Je n'ai pas cette information, je te conseille de contacter l'institut."

## CONTEXTE CLIENT
{context_client}

## CONNAISSANCES MÉTIER
{connaissances_metier}
"""


def format_unified_context(context: str) -> str:
    """
    Formate le contexte unifié mémoire pour le prompt.
    
    Args:
        context: Contexte brut depuis MemorySystem
        
    Returns:
        Contexte formaté pour le prompt
    """
    if not context or context.strip() == "":
        return "*Nouvelle cliente - aucun historique*"
    return context


def format_rag_results(results: str) -> str:
    """
    Formate les résultats RAG pour le prompt.
    
    Args:
        results: Résultats RAG bruts
        
    Returns:
        Résultats formatés pour le prompt
    """
    if not results or results.strip() == "":
        return "*Aucune documentation trouvée - utilise search_knowledge*"
    return results


def build_agent_system_prompt(
    context: str = "",
    rag_results: str = "",
    available_tools: Optional[List[str]] = None
) -> str:
    """
    Construit le prompt système complet pour l'agent Mina.
    
    Args:
        context: Contexte mémoire client
        rag_results: Résultats RAG optionnels
        available_tools: Liste des noms d'outils disponibles
        
    Returns:
        Prompt système complet
    """
    # Section outils
    if available_tools:
        tools_section = MCP_TOOLS_DESCRIPTION
    else:
        tools_section = "*Aucun outil disponible - réponds avec tes connaissances*"
    
    # Formater le contexte
    context_formatted = format_unified_context(context)
    
    # Formater les résultats RAG
    rag_formatted = format_rag_results(rag_results)
    
    # Construire le prompt final
    prompt = AGENT_SYSTEM_PROMPT_TEMPLATE.format(
        tools_section=tools_section,
        context_client=context_formatted,
        connaissances_metier=rag_formatted
    )
    
    return prompt


def build_react_prompt(
    user_input: str,
    context: str = "",
    iteration: int = 1,
    max_iterations: int = 5,
    previous_actions: Optional[List[Dict]] = None
) -> str:
    """
    Construit le prompt ReAct pour une itération.
    
    Args:
        user_input: Question originale de l'utilisateur
        context: Contexte client
        iteration: Numéro d'itération actuelle
        max_iterations: Nombre max d'itérations
        previous_actions: Liste des actions précédentes
        
    Returns:
        Prompt ReAct pour continuer la boucle
    """
    prompt_parts = [
        f"## Itération {iteration}/{max_iterations}",
        "",
        f"**Question originale:** {user_input}",
        ""
    ]
    
    # Ajouter les actions précédentes
    if previous_actions:
        prompt_parts.append("**Actions précédentes:**")
        for i, action in enumerate(previous_actions, 1):
            tool_name = action.get("tool", "unknown")
            result = action.get("result", {})
            success = result.get("success", False)
            status = "✅" if success else "❌"
            
            # Résumé du résultat
            if success and "data" in result:
                result_summary = str(result["data"])[:200] + "..." if len(str(result.get("data", ""))) > 200 else str(result.get("data", ""))
            elif "error" in result:
                result_summary = f"Erreur: {result['error']}"
            else:
                result_summary = str(result)[:200]
            
            prompt_parts.append(f"{i}. {status} **{tool_name}** → {result_summary}")
        prompt_parts.append("")
    
    # Instructions pour la suite
    prompt_parts.extend([
        "**Instructions:**",
        "- Si tu as assez d'informations, réponds directement à la cliente",
        "- Sinon, utilise un autre outil pour compléter",
        f"- Il te reste {max_iterations - iteration} itérations",
        "",
        "**Ta réponse ou prochaine action:**"
    ])
    
    return "\n".join(prompt_parts)
