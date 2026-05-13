import os
import asyncio
from google import genai
from google.genai import types

class MinaRealtimeOrchestrator:
    """Standard 2026 : Agenticité Pure & Latence < 500ms"""
    def __init__(self):
        self.client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"), http_options={'api_version': 'v1alpha'})
        self.model_id = "gemini-2.0-flash"

    async def process_live(self, user_input):
        # Boucle ReAct autonome (Observe-Think-Act)
        config = types.GenerateContentConfig(
            system_instruction="Tu es MINA (Body Touch). Utilise les outils MCP. Pas de hardcode.",
            temperature=0.7
        )
        async for chunk in self.client.aio.models.generate_content_stream(
            model=self.model_id, contents=user_input, config=config
        ):
            yield chunk.text
