"""
FastAPI Server & REST API for Autonomous Enterprise Workflow Agent.
Provides endpoints for claim processing, state inspection, caseworker HITL sign-off,
sample claim loading, and frontend static serving.
"""

from __future__ import annotations
import os
from pathlib import Path
from typing import Optional, List
from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import json
from fastapi.responses import HTMLResponse, FileResponse, StreamingResponse
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent / ".env")

from src.pipeline import run_pipeline, run_pipeline_stream, resume_pipeline, load_state, list_states
from src.models.schemas import ClaimState, DecisionOutcome, CaseworkerDecision

app = FastAPI(
    title="Autonomous Enterprise Workflow Agent API",
    description="Backend API for Healthcare & Insurance Claim Document Review Agent",
    version="1.0.0"
)

# Enable CORS for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ProcessClaimRequest(BaseModel):
    raw_text: str
    claim_id: Optional[str] = None


class ResumeClaimRequest(BaseModel):
    claim_id: str
    action: str  # "approve" or "reject"
    notes: Optional[str] = "Approved following caseworker review."
    caseworker_signature: Optional[str] = "Senior Caseworker J. Smith, RN"


@app.get("/api/health")
def health_check():
    return {"status": "online", "system": "Autonomous Enterprise Workflow Agent", "version": "1.0.0"}


@app.get("/api/samples")
def get_sample_claims():
    """Returns pre-loaded sample claim files for 1-click testing in UI."""
    sample_dir = Path("sample_claims")
    samples = []
    if sample_dir.exists():
        for f in sample_dir.glob("*.txt"):
            try:
                with open(f, "r", encoding="utf-8") as file:
                    content = file.read()
                    samples.append({
                        "filename": f.name,
                        "title": f.stem.replace("_", " ").title(),
                        "content": content
                    })
            except Exception:
                pass
    return sorted(samples, key=lambda x: x["filename"])


@app.post("/api/workflow/process", response_model=ClaimState)
def process_claim_text(req: ProcessClaimRequest):
    """Ingests raw claim text and executes multi-step workflow pipeline."""
    if not req.raw_text or len(req.raw_text.strip()) < 10:
        raise HTTPException(status_code=400, detail="Raw text content is too short or invalid.")
    try:
        state = run_pipeline(req.raw_text, req.claim_id)
        return state
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Workflow execution failed: {str(e)}")


@app.post("/api/workflow/process-stream")
async def process_claim_stream(req: ProcessClaimRequest):
    """Streams real-time backend agent execution progress events via Server-Sent Events (SSE)."""
    if not req.raw_text or len(req.raw_text.strip()) < 10:
        raise HTTPException(status_code=400, detail="Raw text content is too short or invalid.")

    async def event_generator():
        async for event in run_pipeline_stream(req.raw_text, req.claim_id):
            yield f"data: {json.dumps(event)}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@app.post("/api/workflow/upload", response_model=ClaimState)
async def process_claim_file(file: UploadFile = File(...)):
    """Uploads a document file (.txt or PDF) and executes workflow."""
    try:
        content = await file.read()
        text = content.decode("utf-8", errors="ignore")
        if not text or len(text.strip()) < 10:
            raise HTTPException(status_code=400, detail="Uploaded file is empty or could not be parsed.")
        state = run_pipeline(text)
        return state
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"File processing error: {str(e)}")


@app.post("/api/workflow/resume", response_model=ClaimState)
def resume_claim_workflow(req: ResumeClaimRequest):
    """Submits human caseworker sign-off and resumes a halted HITL claim."""
    outcome = DecisionOutcome.APPROVED if req.action.lower() == "approve" else DecisionOutcome.REJECTED
    decision = CaseworkerDecision(
        action=outcome,
        notes=req.notes or "",
        caseworker_signature=req.caseworker_signature or "Senior Caseworker"
    )
    try:
        updated_state = resume_pipeline(req.claim_id, decision)
        return updated_state
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to resume workflow: {str(e)}")


@app.get("/api/claims", response_model=List[ClaimState])
def get_all_claims():
    """Lists all persisted claims from state storage."""
    return list_states()


@app.get("/api/claims/{claim_id}", response_model=ClaimState)
def get_claim_by_id(claim_id: str):
    """Fetches details for a specific claim by ID."""
    state = load_state(claim_id)
    if not state:
        raise HTTPException(status_code=404, detail=f"Claim ID '{claim_id}' not found.")
    return state


# Mount static frontend directory if built
frontend_dist = Path("frontend/dist")
if frontend_dist.exists():
    app.mount("/assets", StaticFiles(directory=frontend_dist / "assets"), name="assets")

    @app.get("/{full_path:path}")
    def serve_frontend(full_path: str):
        file_path = frontend_dist / full_path
        if file_path.exists() and file_path.is_file():
            return FileResponse(file_path)
        return FileResponse(frontend_dist / "index.html")


if __name__ == "__main__":
    import uvicorn
    print("Starting Autonomous Enterprise Workflow Agent Web Server on http://localhost:8000 ...")
    uvicorn.run(app, host="0.0.0.0", port=8000)
