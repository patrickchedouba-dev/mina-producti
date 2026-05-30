"""
API REST Mina V2 - Institut Laurence

Endpoints:
- POST /conversation : Message avec Mina
- GET /health : Santé service
- GET /metrics : Métriques Prometheus
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional, List
import logging
import os
import pathlib

logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Mina API",
    version="2.0",
    description="API REST pour Mina - Assistant IA Body Minute"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Servir les fichiers frontend
_BASE_DIR = pathlib.Path(__file__).parent.parent
app.mount("/static", StaticFiles(directory=str(_BASE_DIR / "static")), name="static")
app.mount("/frontend", StaticFiles(directory=str(_BASE_DIR / "frontend")), name="frontend")


class ConversationRequest(BaseModel):
    user_input: str
    session_id: str
    institut_id: str = "laurence_01"
    client_id: Optional[str] = None


class ConversationResponse(BaseModel):
    response: str
    agents_called: List[str]
    processing_time_ms: int
    success: bool
    error: Optional[str] = None


# Lazy load orchestrator
_orchestrator = None

def get_orchestrator():
    global _orchestrator
    if _orchestrator is None:
        from backend.orchestrator_runtime import get_orchestrator_v2
        _orchestrator = get_orchestrator_v2()
    return _orchestrator


@app.post("/conversation", response_model=ConversationResponse)
async def conversation(request: ConversationRequest):
    """
    Endpoint principal conversation avec Mina
    """
    try:
        orchestrator = get_orchestrator()
        
        result = orchestrator.process_message(
            user_input=request.user_input,
            session_id=request.session_id,
            institut_id=request.institut_id,
            client_id=request.client_id
        )
        
        return ConversationResponse(
            response=result.response,
            agents_called=result.agents_called,
            processing_time_ms=result.processing_time_ms,
            success=result.success,
            error=result.error
        )
        
    except Exception as e:
        # P0 SECURITY FIX: Logger stack trace côté serveur, masquer de l'API
        logger.error(
            f"Conversation error for session {request.session_id}",
            exc_info=True,  # Capture full stack trace dans logs
            extra={
                "session_id": request.session_id,
                "institut_id": request.institut_id,
                "user_input_length": len(request.user_input)
            }
        )
        
        # Retourner message générique au client (JAMAIS de détails techniques)
        raise HTTPException(
            status_code=500,
            detail="Une erreur temporaire est survenue. Veuillez réessayer dans quelques instants."
        )


@app.get("/health")
async def health():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "version": "2.0",
        "service": "mina-orchestrator",
        "institut": os.getenv("INSTITUT_ID", "unknown")
    }


@app.get("/metrics")
async def metrics():
    """Métriques format Prometheus"""
    try:
        from backend.agent.metrics_exporter import get_prometheus_metrics
        return get_prometheus_metrics()
    except Exception as e:
        return {"error": str(e)}


@app.get("/metrics/json")
async def metrics_json():
    """Métriques format JSON"""
    try:
        from backend.agent.metrics_exporter import get_metrics_json
        return get_metrics_json()
    except Exception as e:
        return {"error": str(e)}


@app.get("/health/detailed")
async def health_detailed():
    """Health check détaillé avec métriques Regret-Zero"""
    try:
        from backend.agent.metrics_exporter import get_health_status
        return get_health_status()
    except Exception as e:
        return {"status": "unknown", "error": str(e)}


@app.get("/regret/insights/{institut_id}")
async def regret_insights(institut_id: str, days: int = 30):
    """Insights regret pour un institut"""
    try:
        from backend.agent.regret_calculator import get_regret_calculator
        calc = get_regret_calculator()
        return calc.get_institut_insights(institut_id, days)
    except Exception as e:
        return {"error": str(e)}


@app.get("/experiments/{institut_id}")
async def get_experiments(institut_id: str):
    """Liste les expériences A/B pour un institut"""
    try:
        from backend.agent.ab_testing import get_ab_manager
        manager = get_ab_manager()
        exp = manager.get_active_experiment(institut_id)
        if exp:
            return exp.to_dict()
        return {"message": "No active experiment"}
    except Exception as e:
        return {"error": str(e)}


@app.get("/")
async def root():
    """Interface bêta MINA"""
    beta_path = _BASE_DIR / "frontend" / "mina_beta.html"
    if beta_path.exists():
        return FileResponse(str(beta_path))
    return {"message": "Mina API v2.0", "docs": "/docs", "health": "/health"}

