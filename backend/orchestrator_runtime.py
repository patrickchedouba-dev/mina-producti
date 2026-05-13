"""
Orchestrator Runtime V2 pour Mina.

Architecture multi-agents avec:
- Supervisor routing
- Agents spécialisés (conversation, diagnosis, recommendation, booking, memory, analytics)
- MCP servers (redis, postgres, qdrant, vision)
- Logging structuré
"""

import os
import re
import json
import logging
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from datetime import datetime

from .llm import get_llm_provider, get_resilient_provider, LLMResponse

from .logging_handler import InteractionLog, get_logging_handler

logger = logging.getLogger(__name__)

# Paths
PROMPTS_DIR = Path(__file__).parent.parent / "prompts"
MODEL_NAME = "gemini-2.0-flash"
MAX_ITERATIONS = 5


@dataclass
class AgentDecision:
    """Décision du supervisor."""
    agents: List[str] = field(default_factory=list)
    reasoning: str = ""
    priority: int = 1


@dataclass
class OrchestratorResponse:
    """Réponse de l'orchestrateur V2."""
    response: str
    agents_called: List[str] = field(default_factory=list)
    tools_called: List[Dict] = field(default_factory=list)
    iterations: int = 0
    processing_time_ms: int = 0
    success: bool = True
    error: Optional[str] = None


class MinaOrchestratorV2:
    """
    Orchestrateur V2 Multi-Agents pour Mina.
    
    Workflow:
    1. Charger contexte (mémoire client)
    2. Supervisor décide quel(s) agent(s) mobiliser
    3. Exécuter les agents avec leurs outils MCP
    4. Logger et retourner la réponse
    """
    
    def __init__(self):
        self._model = None
        self._mcp = None
        self._memory = None
        self._logging = None
        self._prompts = {}
        self._routing_rules = []
        self._response_cache = None
        self._context_cache = None
        self._counterfactual = None  # Shadow mode agent
        self._outcome_logger = None
        self._initialized = False
    
    def _ensure_init(self):
        """Initialisation lazy."""
        if self._initialized:
            return
        
        # LLM Provider Résilient (Gemini → Claude → Degraded)
        # Ne lève JAMAIS d'exception
        self._llm = get_resilient_provider()
        logger.info(f"🛡️ Resilient LLM Provider: {self._llm.get_active_provider()}")
        
        # MCP
        try:
            from backend.mcp import get_mcp_client
            self._mcp = get_mcp_client()
            logger.info(f"🔧 MCP: {len(self._mcp.get_tool_names())} outils")
        except Exception as e:
            logger.warning(f"⚠️ MCP: {e}")
        
        # Memory
        try:
            from backend.memory import get_memory_system
            self._memory = get_memory_system()
            logger.info("🧠 Memory connecté")
        except Exception as e:
            logger.warning(f"⚠️ Memory: {e}")
        
        # Logging
        self._logging = get_logging_handler()
        
        # Cache Layer
        try:
            from .cache_layer import get_response_cache, get_context_cache
            self._response_cache = get_response_cache()
            self._context_cache = get_context_cache()
            logger.info("💾 Cache Layer connecté")
        except Exception as e:
            logger.warning(f"⚠️ Cache: {e}")
        
        # Counterfactual Agent (shadow mode)
        if os.getenv("MINA_COUNTERFACTUAL_ENABLED", "false").lower() == "true":
            try:
                from .agent.counterfactual import get_counterfactual_agent
                from .agent.outcome_logger import get_outcome_logger
                self._counterfactual = get_counterfactual_agent()
                self._outcome_logger = get_outcome_logger()
                logger.info("🔮 Counterfactual Agent (shadow mode) activé")
            except Exception as e:
                logger.warning(f"⚠️ Counterfactual: {e}")
        
        # Charger prompts
        self._load_prompts()
        self._load_routing_rules()
        
        self._initialized = True
        logger.info("✅ MinaOrchestratorV2 initialisé")
    
    def _load_prompts(self):
        """Charge les prompts XML."""
        agent_files = {
            "supervisor": "01_system_prompt_supervisor.xml",
            "rgpd": "02_rgpd_compliance.xml",
            "conversation": "03_conversation_agent.xml",
            "diagnosis": "04_diagnosis_agent.xml",
            "recommendation": "05_recommendation_agent.xml",
            "booking": "06_booking_agent.xml",
            "memory": "07_memory_agent.xml",
            "analytics": "08_analytics_agent.xml"
        }
        
        for name, filename in agent_files.items():
            path = PROMPTS_DIR / filename
            if path.exists():
                with open(path, "r", encoding="utf-8") as f:
                    self._prompts[name] = f.read()
                logger.debug(f"📄 Loaded: {name}")
    
    def _load_routing_rules(self):
        """Charge les règles de routing du supervisor."""
        self._routing_rules = [
            (r"bonjour|salut|coucou|hello|hey", ["conversation"]),
            (r"peau|acné|rides?|sèche|grasse|mixte|sensible|rougeur", ["diagnosis", "recommendation"]),
            (r"rendez-vous|réserv|disponib|horaire|rdv", ["booking"]),
            # Memory patterns - AVANT recommendation pour capturer "conseillé" dans contexte mémoire
            (r"historique|préférence|profil|souvien|dernière fois|déjà|aviez|m'aviez|conseillé[es]?.*\?|rappel", ["memory", "conversation"]),
            (r"supprime|efface|oublie.*données|rgpd", ["memory"]),
            # Recommendation en dernier pour éviter conflit avec memory
            (r"produit|recommande|conseil|soin|crème|sérum", ["recommendation"]),
        ]
    
    def _get_institut_policy(self, institut_id: Optional[str]) -> Dict:
        """Récupère la policy apprise pour un institut."""
        if not institut_id:
            return {}
        
        try:
            from backend.agent.policy_updater import get_policy_updater
            return get_policy_updater().get_active_policy(institut_id)
        except:
            return {}
    
    def _route_to_agents(self, user_input: str, institut_id: Optional[str] = None) -> AgentDecision:
        """
        Détermine quel(s) agent(s) appeler.
        
        Utilise les policies apprises si disponibles.
        """
        input_lower = user_input.lower()
        policy = self._get_institut_policy(institut_id)
        
        # Base routing
        for pattern, agents in self._routing_rules:
            if re.search(pattern, input_lower):
                # Apply policy adjustments if available
                adjusted_agents = self._apply_policy_to_agents(agents, policy, input_lower)
                
                return AgentDecision(
                    agents=adjusted_agents,
                    reasoning=f"Pattern matched: {pattern}" + (f" (policy: {institut_id})" if policy else ""),
                    priority=1
                )
        
        # Fallback: conversation
        return AgentDecision(
            agents=["conversation"],
            reasoning="Default fallback",
            priority=1
        )
    
    def _apply_policy_to_agents(self, agents: List[str], policy: Dict, user_input: str) -> List[str]:
        """
        Applique les ajustements de policy aux agents sélectionnés.
        
        Basé sur les insights de regret:
        - budget_first: Favorise alternatives moins chères
        - premium_acceptance: N'hésite pas sur le premium
        - safety_priority: Privilégie la sécurité
        """
        if not policy or not policy.get("routing"):
            return agents
        
        routing = policy.get("routing", {})
        adjusted = list(agents)
        
        # Si budget_first élevé et recommendation présent, ajouter conversation avant
        if routing.get("budget_first", 0) > 0.6 and "recommendation" in adjusted:
            # Ajouter conversation pour tempérer les recos
            if "conversation" not in adjusted:
                adjusted.insert(0, "conversation")
        
        # Si safety_priority élevé, s'assurer que diagnosis précède recommendation
        if routing.get("safety_priority", 0) > 0.7:
            if "recommendation" in adjusted and "diagnosis" not in adjusted:
                idx = adjusted.index("recommendation")
                adjusted.insert(idx, "diagnosis")
        
        return adjusted
    
    async def load_context(
        self,
        session_id: str,
        client_id: Optional[str],
        institut_id: Optional[str]
    ) -> str:
        """Charge le contexte unifié."""
        if not self._memory:
            return ""
        
        try:
            ctx = self._memory.get_unified_context(session_id, client_id)
            context = ctx.to_prompt_context()
            if institut_id:
                context += f"\nInstitut: {institut_id}"
            return context
        except Exception as e:
            logger.warning(f"⚠️ Context load: {e}")
            return ""
    
    def _build_agent_prompt(self, agent_id: str, context: str, user_input: str) -> str:
        """Construit le prompt pour un agent spécifique."""
        agent_prompt = self._prompts.get(agent_id, "")
        rgpd_prompt = self._prompts.get("rgpd", "")
        
        return f"""Tu es Mina, conseillère Body Minute.

{agent_prompt}

--- RÈGLES RGPD ---
{rgpd_prompt[:500]}

--- CONTEXTE CLIENT ---
{context if context else "Nouveau client"}

--- QUESTION ---
{user_input}

Réponds en 2-3 phrases maximum, ton chaleureux, tutoyant.
"""
    
    def _execute_tool_if_needed(self, agent_id: str, user_input: str) -> Optional[Dict]:
        """Exécute un outil MCP si nécessaire pour cet agent."""
        if not self._mcp:
            return None
        
        tools_map = {
            "diagnosis": ("analyze_skin_image", None),
            "recommendation": ("search_knowledge", {"query": user_input, "collection": "bodyminute_products"}),
            "memory": ("get_client_context", None),
        }
        
        if agent_id in tools_map:
            tool_name, args = tools_map[agent_id]
            if tool_name == "search_knowledge" and args:
                try:
                    return self._mcp.execute_tool(tool_name, args)
                except Exception as e:
                    logger.warning(f"⚠️ Tool {tool_name}: {e}")
        
        return None
    
    def process_message(
        self,
        user_input: str,
        session_id: str,
        institut_id: Optional[str] = None,
        client_id: Optional[str] = None
    ) -> OrchestratorResponse:
        """
        Traite un message utilisateur (version synchrone).
        
        Args:
            user_input: Message utilisateur
            session_id: ID session
            institut_id: ID institut (optionnel)
            client_id: ID client (optionnel)
        """
        import time
        timings = {}
        
        # === T0: Start ===
        t0 = time.perf_counter()
        start_time = datetime.now()
        self._ensure_init()
        timings["init"] = int((time.perf_counter() - t0) * 1000)
        
        logger.info(f"🚀 [V2] '{user_input[:40]}...'")
        
        # === CACHE CHECK (early return) ===
        if self._response_cache:
            t_cache = time.perf_counter()
            cached = self._response_cache.get(user_input, institut_id)
            cache_check_time = int((time.perf_counter() - t_cache) * 1000)
            
            if cached:
                processing_time = int((datetime.now() - start_time).total_seconds() * 1000)
                logger.info(f"🎯 [CACHE HIT] {processing_time}ms (check={cache_check_time}ms)")
                return OrchestratorResponse(
                    response=cached.get("response", ""),
                    agents_called=["cache"],
                    tools_called=[],
                    iterations=0,
                    processing_time_ms=processing_time,
                    success=True
                )
        
        # === T1: Context Load ===
        t1 = time.perf_counter()
        import asyncio
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        context = loop.run_until_complete(
            self.load_context(session_id, client_id, institut_id)
        )
        timings["context_load"] = int((time.perf_counter() - t1) * 1000)
        
        # === T2: Routing (policy-aware) ===
        t2 = time.perf_counter()
        decision = self._route_to_agents(user_input, institut_id)
        timings["routing"] = int((time.perf_counter() - t2) * 1000)
        logger.info(f"🎯 Agents: {decision.agents}")
        
        # === T3: Execute Agents ===
        tools_called = []
        responses = []
        timings["tools"] = []
        timings["llm_calls"] = []
        
        try:
            for agent_id in decision.agents:
                # Exécuter outil si nécessaire
                t_tool = time.perf_counter()
                tool_result = self._execute_tool_if_needed(agent_id, user_input)
                tool_time = int((time.perf_counter() - t_tool) * 1000)
                
                if tool_result:
                    tools_called.append({"agent": agent_id, "result": tool_result, "time_ms": tool_time})
                    timings["tools"].append({"agent": agent_id, "time_ms": tool_time})
                    context += f"\n\n[Résultat {agent_id}]: {json.dumps(tool_result, ensure_ascii=False)[:300]}"
                
                # Générer réponse agent via LLM Provider
                t_llm = time.perf_counter()
                prompt = self._build_agent_prompt(agent_id, context, user_input)
                
                messages = [{"role": "user", "content": prompt}]
                llm_response = self._llm.generate_sync(messages)
                agent_response = llm_response.text if llm_response.text else ""
                llm_time = int((time.perf_counter() - t_llm) * 1000)
                timings["llm_calls"].append({"agent": agent_id, "time_ms": llm_time})
                
                if agent_response:
                    responses.append(agent_response)
                    logger.info(f"✅ {agent_id}: {len(agent_response)} chars, {llm_time}ms LLM")
            
            # Synthèse finale (premier agent ou combinaison)
            final_response = responses[0] if responses else "Désolée, peux-tu reformuler ?"
            
            # === T4: Store in Memory ===
            t_store = time.perf_counter()
            if self._memory:
                try:
                    self._memory.store_interaction(
                        session_id=session_id,
                        client_id=client_id,
                        user_message=user_input,
                        assistant_message=final_response
                    )
                except Exception as e:
                    logger.warning(f"⚠️ Store: {e}")
            timings["memory_store"] = int((time.perf_counter() - t_store) * 1000)
            
            processing_time = int((datetime.now() - start_time).total_seconds() * 1000)
            
            # === Performance Summary ===
            total_tool_time = sum(t.get("time_ms", 0) for t in timings.get("tools", []))
            total_llm_time = sum(t.get("time_ms", 0) for t in timings.get("llm_calls", []))
            
            logger.info(f"⏱️ [PERF] init={timings['init']}ms | ctx={timings['context_load']}ms | route={timings['routing']}ms | tools={total_tool_time}ms | llm={total_llm_time}ms | store={timings['memory_store']}ms | TOTAL={processing_time}ms")
            
            # === CACHE SET (for cacheable responses) ===
            if self._response_cache:
                try:
                    self._response_cache.set(
                        user_input=user_input,
                        response={"response": final_response, "agents": decision.agents},
                        institut_id=institut_id
                    )
                except:
                    pass
            
            # Logging structuré
            log = InteractionLog(
                session_id=session_id,
                client_id=client_id,
                institut_id=institut_id,
                user_input=user_input,
                response=final_response,
                agents_called=decision.agents,
                supervisor_decision=decision.reasoning,
                tools_called=tools_called,
                latency_ms=processing_time,
                iterations=len(decision.agents),
                success=True
            )
            self._logging.log_interaction(log)
            
            # === COUNTERFACTUAL SHADOW MODE ===
            # Générer chemins alternatifs en arrière-plan (non-bloquant)
            if self._counterfactual and os.getenv("MINA_COUNTERFACTUAL_ENABLED", "false").lower() == "true":
                try:
                    shadow_paths = self._counterfactual.generate_shadow_paths(
                        real_response=final_response,
                        user_input=user_input,
                        context={"institut_id": institut_id, "agents": decision.agents}
                    )
                    
                    if shadow_paths and self._outcome_logger:
                        cf_decision = self._counterfactual.create_decision_record(
                            session_id=session_id,
                            client_id=client_id,
                            institut_id=institut_id,
                            user_input=user_input,
                            real_response=final_response,
                            context={"agents": decision.agents, "tools": [t.get("agent") for t in tools_called]},
                            shadow_paths=shadow_paths
                        )
                        self._outcome_logger.log_decision(cf_decision)
                        logger.info(f"🔮 Shadow paths logged: {len(shadow_paths)}")
                except Exception as e:
                    logger.debug(f"⚠️ Counterfactual: {e}")
            
            logger.info(f"🏁 {processing_time}ms, {len(decision.agents)} agents")
            
            return OrchestratorResponse(
                response=final_response,
                agents_called=decision.agents,
                tools_called=tools_called,
                iterations=len(decision.agents),
                processing_time_ms=processing_time,
                success=True
            )
            
        except Exception as e:
            logger.error(f"❌ Error: {e}")
            processing_time = int((datetime.now() - start_time).total_seconds() * 1000)
            
            # Log error
            log = InteractionLog(
                session_id=session_id,
                client_id=client_id,
                user_input=user_input,
                response=str(e),
                agents_called=decision.agents,
                latency_ms=processing_time,
                success=False,
                error=str(e)
            )
            self._logging.log_interaction(log)
            
            return OrchestratorResponse(
                response=f"Erreur: {str(e)[:50]}",
                agents_called=decision.agents,
                processing_time_ms=processing_time,
                success=False,
                error=str(e)
            )


# Singleton
_orchestrator_v2: Optional[MinaOrchestratorV2] = None


def get_orchestrator_v2() -> MinaOrchestratorV2:
    """Retourne l'instance singleton."""
    global _orchestrator_v2
    if _orchestrator_v2 is None:
        _orchestrator_v2 = MinaOrchestratorV2()
    return _orchestrator_v2
