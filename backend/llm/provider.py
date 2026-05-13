"""
LLM Provider Abstraction pour Mina.

Permet de switcher entre Gemini, Claude, ou autres LLMs
sans modifier le code de l'orchestrateur.
"""

import os
import json
import logging
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

logger = logging.getLogger(__name__)


@dataclass
class LLMResponse:
    """Réponse normalisée d'un LLM."""
    text: str = ""
    tool_calls: List[Dict] = None
    finish_reason: str = "stop"
    usage: Dict = None
    
    def __post_init__(self):
        if self.tool_calls is None:
            self.tool_calls = []
        if self.usage is None:
            self.usage = {"input_tokens": 0, "output_tokens": 0}
    
    @property
    def has_tool_call(self) -> bool:
        return len(self.tool_calls) > 0


class LLMProvider(ABC):
    """Interface abstraite pour les providers LLM."""
    
    @abstractmethod
    async def generate(
        self,
        messages: List[Dict],
        tools: Optional[List[Dict]] = None,
        temperature: float = 0.3,
        max_tokens: int = 500
    ) -> LLMResponse:
        """Génère une réponse à partir des messages."""
        pass
    
    @abstractmethod
    def generate_sync(
        self,
        messages: List[Dict],
        tools: Optional[List[Dict]] = None,
        temperature: float = 0.3,
        max_tokens: int = 500
    ) -> LLMResponse:
        """Version synchrone de generate."""
        pass


class GeminiProvider(LLMProvider):
    """Provider Google Gemini avec retry automatique."""
    
    def __init__(self, model: str = "gemini-2.0-flash-exp"):
        from google import genai
        
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError("GOOGLE_API_KEY not set")
        
        genai.configure(api_key=api_key)
        self._model_name = model
        self._model = genai.GenerativeModel(model)
        logger.info(f"🤖 GeminiProvider initialisé: {model}")
    
    async def generate(
        self,
        messages: List[Dict],
        tools: Optional[List[Dict]] = None,
        temperature: float = 0.3,
        max_tokens: int = 500
    ) -> LLMResponse:
        """Génération asynchrone (wrapper sync pour Gemini)."""
        return self.generate_sync(messages, tools, temperature, max_tokens)
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True
    )
    def generate_sync(
        self,
        messages: List[Dict],
        tools: Optional[List[Dict]] = None,
        temperature: float = 0.3,
        max_tokens: int = 500
    ) -> LLMResponse:
        """Génération synchrone Gemini avec retry automatique."""
        # Convertir messages en prompt
        prompt = self._format_messages(messages)
        
        # Préparer tools si présents
        gemini_tools = None
        if tools:
            gemini_tools = [{"function_declarations": tools}]
        
        # Générer avec timeout de 30 secondes
        config = {
            "temperature": temperature,
            "max_output_tokens": max_tokens
        }
        
        logger.debug(f"🔄 Gemini call: {len(prompt)} chars")
        
        # P0 FIX: Timeout 30s pour éviter blocage indéfini
        import signal
        
        def timeout_handler(signum, frame):
            raise TimeoutError("Gemini LLM timeout after 30 seconds")
        
        # Set timeout (Unix only, fallback sans timeout sur Windows)
        old_handler = None
        try:
            old_handler = signal.signal(signal.SIGALRM, timeout_handler)
            signal.alarm(30)  # 30 secondes
        except (AttributeError, ValueError):
            pass  # Windows ou thread non-main
        
        try:
            response = self._model.generate_content(
                prompt,
                tools=gemini_tools,
                generation_config=config
            )
        finally:
            # Reset alarm
            try:
                signal.alarm(0)
                if old_handler:
                    signal.signal(signal.SIGALRM, old_handler)
            except (AttributeError, ValueError):
                pass
        
        return self._parse_response(response)
    
    def _format_messages(self, messages: List[Dict]) -> str:
        """Convertit messages en prompt texte."""
        parts = []
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role == "system":
                parts.append(content)
            elif role == "user":
                parts.append(f"\nUtilisateur: {content}")
            elif role == "assistant":
                parts.append(f"\nAssistant: {content}")
        return "\n".join(parts)
    
    def _parse_response(self, response) -> LLMResponse:
        """Parse la réponse Gemini vers LLMResponse."""
        text = ""
        tool_calls = []
        
        try:
            for candidate in response.candidates:
                for part in candidate.content.parts:
                    if hasattr(part, 'text') and part.text:
                        text = part.text
                    if hasattr(part, 'function_call') and part.function_call:
                        fc = part.function_call
                        tool_calls.append({
                            "name": fc.name,
                            "arguments": dict(fc.args) if fc.args else {}
                        })
        except Exception as e:
            logger.warning(f"Error parsing Gemini response: {e}")
        
        return LLMResponse(
            text=text,
            tool_calls=tool_calls,
            finish_reason="tool_call" if tool_calls else "stop"
        )


class ClaudeProvider(LLMProvider):
    """Provider Anthropic Claude."""
    
    def __init__(self, model: str = "claude-sonnet-4-20250514"):
        try:
            import anthropic
            self._client = anthropic.Anthropic()
            self._async_client = anthropic.AsyncAnthropic()
        except ImportError:
            raise ImportError("pip install anthropic required for ClaudeProvider")
        
        self._model = model
        logger.info(f"🤖 ClaudeProvider initialisé: {model}")
    
    async def generate(
        self,
        messages: List[Dict],
        tools: Optional[List[Dict]] = None,
        temperature: float = 0.3,
        max_tokens: int = 500
    ) -> LLMResponse:
        """Génération asynchrone Claude."""
        # Extraire system message
        system = ""
        claude_messages = []
        
        for msg in messages:
            if msg.get("role") == "system":
                system = msg.get("content", "")
            else:
                claude_messages.append(msg)
        
        # Convertir tools format Gemini → Claude
        claude_tools = self._convert_tools(tools) if tools else None
        
        kwargs = {
            "model": self._model,
            "messages": claude_messages,
            "max_tokens": max_tokens,
            "temperature": temperature
        }
        
        if system:
            kwargs["system"] = system
        if claude_tools:
            kwargs["tools"] = claude_tools
        
        response = await self._async_client.messages.create(**kwargs)
        return self._parse_response(response)
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True
    )
    def generate_sync(
        self,
        messages: List[Dict],
        tools: Optional[List[Dict]] = None,
        temperature: float = 0.3,
        max_tokens: int = 500
    ) -> LLMResponse:
        """Génération synchrone Claude avec retry automatique."""
        system = ""
        claude_messages = []
        
        for msg in messages:
            if msg.get("role") == "system":
                system = msg.get("content", "")
            else:
                claude_messages.append(msg)
        
        claude_tools = self._convert_tools(tools) if tools else None
        
        # P0 FIX: Timeout 30s pour éviter blocage indéfini
        kwargs = {
            "model": self._model,
            "messages": claude_messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "timeout": 30.0  # 30 secondes MAX - paramètre Anthropic SDK
        }
        
        if system:
            kwargs["system"] = system
        if claude_tools:
            kwargs["tools"] = claude_tools
        
        response = self._client.messages.create(**kwargs)
        return self._parse_response(response)
    
    def _convert_tools(self, gemini_tools: List[Dict]) -> List[Dict]:
        """Convertit tools format Gemini → Claude."""
        claude_tools = []
        for tool in gemini_tools:
            claude_tools.append({
                "name": tool.get("name"),
                "description": tool.get("description", ""),
                "input_schema": tool.get("parameters", {"type": "object", "properties": {}})
            })
        return claude_tools
    
    def _parse_response(self, response) -> LLMResponse:
        """Parse la réponse Claude vers LLMResponse."""
        text = ""
        tool_calls = []
        
        for block in response.content:
            if block.type == "text":
                text = block.text
            elif block.type == "tool_use":
                tool_calls.append({
                    "name": block.name,
                    "arguments": block.input
                })
        
        return LLMResponse(
            text=text,
            tool_calls=tool_calls,
            finish_reason="tool_call" if tool_calls else "stop",
            usage={
                "input_tokens": response.usage.input_tokens,
                "output_tokens": response.usage.output_tokens
            }
        )


# ==== Factory ====

_providers: Dict[str, LLMProvider] = {}


def get_llm_provider(provider: str = None) -> LLMProvider:
    """
    Factory pour obtenir un provider LLM.
    
    Args:
        provider: "gemini" ou "claude". Si None, lit LLM_PROVIDER env.
    
    Returns:
        Instance LLMProvider (singleton)
    """
    if provider is None:
        provider = os.getenv("LLM_PROVIDER", "gemini").lower()
    
    if provider in _providers:
        return _providers[provider]
    
    if provider == "gemini":
        model = os.getenv("GEMINI_MODEL", "gemini-2.0-flash-exp")
        _providers[provider] = GeminiProvider(model)
    elif provider == "claude":
        model = os.getenv("CLAUDE_MODEL", "claude-sonnet-4-20250514")
        _providers[provider] = ClaudeProvider(model)
    else:
        raise ValueError(f"Unknown LLM provider: {provider}. Use 'gemini' or 'claude'.")
    
    return _providers[provider]
