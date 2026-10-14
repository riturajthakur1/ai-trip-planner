"""
FastAPI Server exposing the LangGraph AI Trip Planning Agent.
"""

import uuid
from typing import Dict, List, Optional, Any
from fastapi import FastAPI, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from agent.graph import create_trip_agent_graph
from agent.state import AgentState, TravelSlots
from agent.pdf_generator import build_pdf_itinerary
from data.db import TravelDatabase

app = FastAPI(
    title="Curated India AI Trip Planner API",
    description="Agentic trip planning service using LangGraph and curated non-generic datasets for India",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory session store
sessions: Dict[str, AgentState] = {}
agent_graph = create_trip_agent_graph()


class ChatRequest(BaseModel):
    sessionId: Optional[str] = None
    message: str


class ChatResponse(BaseModel):
    sessionId: str
    message: str
    slots: Dict[str, Any]
    ready_for_itinerary: bool
    itinerary: Optional[Dict[str, Any]] = None
    circuit_id: Optional[str] = None


@app.get("/health")
def health_check():
    return {"status": "ok", "service": "ai-trip-planner"}


@app.get("/api/session")
def create_session():
    new_id = str(uuid.uuid4())
    sessions[new_id] = AgentState()
    return {"sessionId": new_id}


@app.post("/api/chat", response_model=ChatResponse)
def chat_endpoint(req: ChatRequest):
    sess_id = req.sessionId or str(uuid.uuid4())
    if sess_id not in sessions:
        sessions[sess_id] = AgentState()

    current_state = sessions[sess_id]
    # Append user message
    updated_messages = current_state.messages + [{"role": "user", "content": req.message}]
    new_state = AgentState(
        messages=updated_messages,
        slots=current_state.slots,
        circuit_id=current_state.circuit_id,
        itinerary=current_state.itinerary,
        ready_for_itinerary=current_state.ready_for_itinerary
    )

    # Invoke LangGraph
    result = agent_graph.invoke(new_state)
    sessions[sess_id] = AgentState(
        messages=result["messages"],
        slots=result["slots"],
        circuit_id=result.get("circuit_id"),
        itinerary=result.get("itinerary"),
        ready_for_itinerary=result.get("ready_for_itinerary", False),
        assistant_response=result.get("assistant_response")
    )

    itinerary_dict = None
    if result.get("itinerary"):
        itinerary_dict = result["itinerary"].model_dump()

    return ChatResponse(
        sessionId=sess_id,
        message=result.get("assistant_response", ""),
        slots=result["slots"].model_dump(),
        ready_for_itinerary=result.get("ready_for_itinerary", False),
        itinerary=itinerary_dict,
        circuit_id=result.get("circuit_id")
    )


@app.get("/api/session/{session_id}")
def get_session_state(session_id: str):
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    state = sessions[session_id]
    return {
        "sessionId": session_id,
        "slots": state.slots.model_dump(),
        "ready_for_itinerary": state.ready_for_itinerary,
        "circuit_id": state.circuit_id,
        "itinerary": state.itinerary.model_dump() if state.itinerary else None,
        "messages_count": len(state.messages)
    }


@app.get("/api/itinerary/{session_id}/export")
def export_itinerary_markdown(session_id: str):
    if session_id not in sessions or not sessions[session_id].assistant_response:
        raise HTTPException(status_code=404, detail="No generated itinerary found for this session")
    return {"markdown": sessions[session_id].assistant_response}


@app.get("/api/itinerary/{session_id}/pdf")
def export_itinerary_pdf(session_id: str):
    if session_id not in sessions or not sessions[session_id].itinerary:
        raise HTTPException(status_code=404, detail="No generated itinerary found for this session")
    
    state = sessions[session_id]
    pdf_bytes = build_pdf_itinerary(state.itinerary, state.circuit_id)
    cname = state.itinerary.circuit_name.lower().replace(" ", "_").replace("&", "and")
    filename = f"{cname}_{state.itinerary.total_days}days_itinerary.pdf"
    
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )


@app.get("/api/circuits")
def get_available_circuits():
    db = TravelDatabase.get_instance()
    return [c.model_dump() for c in db.dataset.circuits]


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api.server:app", host="0.0.0.0", port=8000, reload=True)
