"""
MINA - FastAPI Application
Interface REST pour Mina
"""

import logging
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
import asyncio

from core.orchestrator import MinaOrchestrator

# Configuration logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Application FastAPI
app = FastAPI(
    title="Mina API",
    description="Assistant IA Body Minute - Architecture Unifiée",
    version="1.0.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # À restreindre en production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuration Mina
CONFIG = {
    'brain_manager': {
        'default_brain': 'claude',
        'brains': {
            'claude': {
                'name': 'Claude Sonnet 4.5',
                'version': '1.0.0',
                'api_key': 'sk-ant-api03-xxx',  # À remplacer par variable env
                'model': 'claude-sonnet-4-20250514'
            }
        }
    },
    'memory_manager': {
        'host': 'localhost',
        'port': 6333,
        'collection': 'body_minute'
    }
}

# Orchestrateur global
orchestrator: Optional[MinaOrchestrator] = None


# Modèles Pydantic
class QueryRequest(BaseModel):
    """Modèle de requête"""
    query: str = Field(..., description="Question ou requête utilisateur")
    user_id: Optional[str] = Field(None, description="Identifiant utilisateur")
    brain: Optional[str] = Field(None, description="Brain spécifique à utiliser")
    memory_limit: Optional[int] = Field(5, description="Nombre de résultats mémoire")
    memory_threshold: Optional[float] = Field(0.7, description="Seuil de pertinence")


class QueryResponse(BaseModel):
    """Modèle de réponse"""
    success: bool
    response: Optional[str] = None
    confidence: Optional[float] = None
    sources: Optional[List[str]] = None
    processing_time: Optional[float] = None
    timestamp: str
    error: Optional[str] = None


class MultiBrainRequest(BaseModel):
    """Requête multi-brain"""
    query: str
    brains: List[str]
    mode: str = Field('sequential', description="Mode: sequential | parallel | cascade")


class HealthResponse(BaseModel):
    """Réponse health check"""
    status: str
    mina_version: str
    initialized: bool
    stats: Dict[str, Any]


# Événements lifecycle
@app.on_event("startup")
async def startup_event():
    """Initialisation au démarrage"""
    global orchestrator
    
    logger.info("🚀 Starting Mina API...")
    
    try:
        orchestrator = MinaOrchestrator(CONFIG)
        
        if await orchestrator.initialize():
            logger.info("✓ Mina Orchestrator initialized successfully")
        else:
            logger.error("✗ Mina Orchestrator initialization failed")
            
    except Exception as e:
        logger.error(f"Startup failed: {e}")
        raise


@app.on_event("shutdown")
async def shutdown_event():
    """Nettoyage à l'arrêt"""
    global orchestrator
    
    logger.info("Shutting down Mina API...")
    
    if orchestrator:
        await orchestrator.shutdown()
    
    logger.info("Mina API shutdown complete")


# Endpoints
@app.get("/", tags=["Info"])
async def root():
    """Endpoint racine"""
    return {
        "name": "Mina API",
        "version": "1.0.0",
        "description": "Assistant IA Body Minute",
        "status": "operational",
        "architecture": "Claude intégré natif + Qdrant",
        "documentation": "/docs"
    }


@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check():
    """Health check complet"""
    if not orchestrator:
        raise HTTPException(status_code=503, detail="Orchestrator not initialized")
    
    stats = orchestrator.get_stats()
    
    return {
        "status": "healthy" if orchestrator._initialized else "degraded",
        "mina_version": "1.0.0",
        "initialized": orchestrator._initialized,
        "stats": stats
    }


@app.post("/query", response_model=QueryResponse, tags=["Query"])
async def process_query(request: QueryRequest):
    """
    Traite une requête utilisateur
    
    Exemple:
    ```json
    {
        "query": "Quels sont les produits phares Body Minute ?",
        "user_id": "user_123",
        "brain": "claude"
    }
    ```
    """
    if not orchestrator:
        raise HTTPException(status_code=503, detail="Service not ready")
    
    try:
        logger.info(f"Query received: '{request.query[:50]}...'")
        
        options = {
            'memory_limit': request.memory_limit,
            'memory_threshold': request.memory_threshold
        }
        
        result = await orchestrator.process(
            query=request.query,
            user_id=request.user_id,
            brain_name=request.brain,
            options=options
        )
        
        return QueryResponse(
            success=result.get('success', True),
            response=result.get('response'),
            confidence=result.get('confidence'),
            sources=result.get('sources'),
            processing_time=result.get('processing_time'),
            timestamp=result.get('timestamp', datetime.now().isoformat()),
            error=result.get('error')
        )
        
    except Exception as e:
        logger.error(f"Query processing error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/multi-brain", tags=["Query"])
async def multi_brain_query(request: MultiBrainRequest):
    """
    Traite une requête avec plusieurs cerveaux
    
    Modes disponibles:
    - sequential: Traitement séquentiel
    - parallel: Traitement parallèle
    - cascade: Analyse puis traitement
    """
    if not orchestrator:
        raise HTTPException(status_code=503, detail="Service not ready")
    
    try:
        result = await orchestrator.multi_brain_process(
            query=request.query,
            brains=request.brains,
            mode=request.mode
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Multi-brain processing error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/stats", tags=["Info"])
async def get_stats():
    """Statistiques d'utilisation"""
    if not orchestrator:
        raise HTTPException(status_code=503, detail="Service not ready")
    
    return orchestrator.get_stats()


@app.get("/brains", tags=["Info"])
async def list_brains():
    """Liste les brains disponibles"""
    if not orchestrator:
        raise HTTPException(status_code=503, detail="Service not ready")
    
    return orchestrator.brain_manager.get_stats()


@app.get("/capabilities", tags=["Info"])
async def get_capabilities():
    """Liste toutes les capacités disponibles"""
    if not orchestrator:
        raise HTTPException(status_code=503, detail="Service not ready")
    
    return orchestrator.brain_manager.get_all_capabilities()


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket pour streaming temps réel
    
    TODO: Implémenter streaming des réponses
    """
    await websocket.accept()
    
    try:
        while True:
            data = await websocket.receive_text()
            
            # TODO: Traiter et streamer la réponse
            await websocket.send_text(f"Echo: {data}")
            
    except WebSocketDisconnect:
        logger.info("WebSocket disconnected")


# Point d'entrée
if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
