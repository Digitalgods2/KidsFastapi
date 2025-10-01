"""
Workflow routes for KidsKlassiks
Manages the complete adaptation workflow with proper sequencing
"""

from fastapi import APIRouter, Request, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
import asyncio
import json
from typing import Dict, Any

import database_fixed as database
from services.workflow_manager import workflow_manager, WorkflowStage, WorkflowStatus
from services.logger import get_logger
import config

router = APIRouter()
templates = Jinja2Templates(directory="templates")
logger = get_logger("routes.workflow")

# Store WebSocket connections for real-time updates
active_connections: Dict[str, WebSocket] = {}


def get_base_context(request: Request):
    """Get base context variables for all templates"""
    return {
        "request": request,
        "notifications_count": 0,
        "notifications": [],
        "openai_status": bool(config.OPENAI_API_KEY),
        "vertex_status": config.validate_vertex_ai_config()
    }


@router.post("/start/{adaptation_id}")
async def start_workflow(adaptation_id: int, request: Request):
    """
    Start the complete adaptation workflow after creation
    This replaces the old multi-step process with a single automated flow
    """
    try:
        # Get adaptation details
        adaptation = await database.get_adaptation_details(adaptation_id)
        if not adaptation:
            raise HTTPException(status_code=404, detail="Adaptation not found")
        
        book_id = adaptation["book_id"]
        
        # Start the workflow
        workflow_id = await workflow_manager.start_adaptation_workflow(
            book_id=book_id,
            adaptation_id=adaptation_id,
            background=True
        )
        
        logger.info("workflow_started", extra={
            "workflow_id": workflow_id,
            "adaptation_id": adaptation_id,
            "book_id": book_id
        })
        
        # Return response for HTMX
        if request.headers.get("HX-Request"):
            return HTMLResponse(f"""
                <div class="alert alert-info">
                    <i class="bi bi-hourglass-split"></i>
                    <strong>Workflow Started!</strong>
                    <p class="mb-0">Processing your adaptation. This may take several minutes.</p>
                    <p class="mb-0 mt-2">Workflow ID: <code>{workflow_id}</code></p>
                    <div class="mt-3">
                        <a href="/workflow/status/{workflow_id}" class="btn btn-sm btn-primary">
                            <i class="bi bi-eye"></i> View Progress
                        </a>
                    </div>
                </div>
            """)
        
        return JSONResponse({
            "success": True,
            "workflow_id": workflow_id,
            "message": "Workflow started successfully"
        })
        
    except Exception as e:
        logger.error("start_workflow_error", extra={
            "adaptation_id": adaptation_id,
            "error": str(e)
        })
        
        if request.headers.get("HX-Request"):
            return HTMLResponse(f"""
                <div class="alert alert-danger">
                    <i class="bi bi-exclamation-triangle"></i>
                    <strong>Error!</strong> {str(e)}
                </div>
            """, status_code=500)
        
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status/{workflow_id}")
async def workflow_status_page(workflow_id: str, request: Request):
    """Display workflow status page with real-time updates"""
    context = get_base_context(request)
    
    # Get workflow status
    status = workflow_manager.get_workflow_status(workflow_id)
    if not status:
        raise HTTPException(status_code=404, detail="Workflow not found")
    
    # Get adaptation details
    adaptation = await database.get_adaptation_details(status["adaptation_id"])
    book = await database.get_book_details(status["book_id"])
    
    context.update({
        "workflow": status,
        "adaptation": adaptation,
        "book": book,
        "workflow_id": workflow_id
    })
    
    return templates.TemplateResponse("pages/workflow_status.html", context)


@router.get("/api/status/{workflow_id}")
async def get_workflow_status(workflow_id: str):
    """Get workflow status as JSON"""
    status = workflow_manager.get_workflow_status(workflow_id)
    if not status:
        raise HTTPException(status_code=404, detail="Workflow not found")
    
    return JSONResponse({
        "workflow_id": workflow_id,
        "status": status["status"].value,
        "stage": status["stage"].value,
        "progress": status["progress"],
        "stages_completed": [s.value for s in status["stages_completed"]],
        "current_stage_progress": status["current_stage_progress"],
        "started_at": status["started_at"].isoformat() if status.get("started_at") else None,
        "completed_at": status.get("completed_at").isoformat() if status.get("completed_at") else None,
        "errors": status["errors"],
        "last_notification": status["notifications"][-1] if status["notifications"] else None
    })


@router.websocket("/ws/{workflow_id}")
async def workflow_websocket(websocket: WebSocket, workflow_id: str):
    """
    WebSocket endpoint for real-time workflow updates
    """
    await websocket.accept()
    active_connections[workflow_id] = websocket
    
    try:
        # Send initial status
        status = workflow_manager.get_workflow_status(workflow_id)
        if status:
            await websocket.send_json({
                "type": "status",
                "data": {
                    "workflow_id": workflow_id,
                    "status": status["status"].value,
                    "stage": status["stage"].value,
                    "progress": status["progress"]
                }
            })
        
        # Keep connection alive and send updates
        while True:
            # Wait for messages or send periodic status
            try:
                data = await asyncio.wait_for(websocket.receive_text(), timeout=30)
                # Handle any client messages if needed
            except asyncio.TimeoutError:
                # Send heartbeat
                await websocket.send_json({"type": "heartbeat"})
                
    except WebSocketDisconnect:
        if workflow_id in active_connections:
            del active_connections[workflow_id]
        logger.info("websocket_disconnected", extra={"workflow_id": workflow_id})


async def send_workflow_update(workflow_id: str, update_data: Dict[str, Any]):
    """
    Send update to connected WebSocket client
    """
    if workflow_id in active_connections:
        websocket = active_connections[workflow_id]
        try:
            await websocket.send_json({
                "type": "update",
                "data": update_data
            })
        except Exception as e:
            logger.error("websocket_send_error", extra={
                "workflow_id": workflow_id,
                "error": str(e)
            })
            # Remove dead connection
            if workflow_id in active_connections:
                del active_connections[workflow_id]


# Workflow progress callback for real-time updates
async def workflow_progress_callback(update_data: Dict[str, Any]):
    """
    Callback function to be used by WorkflowManager for progress updates
    """
    workflow_id = update_data.get("workflow_id")
    if workflow_id:
        await send_workflow_update(workflow_id, update_data)


@router.post("/pause/{workflow_id}")
async def pause_workflow(workflow_id: str):
    """Pause a running workflow"""
    success = await workflow_manager.pause_workflow(workflow_id)
    if success:
        return JSONResponse({"success": True, "message": "Workflow paused"})
    else:
        raise HTTPException(status_code=400, detail="Cannot pause workflow")


@router.post("/resume/{workflow_id}")
async def resume_workflow(workflow_id: str):
    """Resume a paused workflow"""
    success = await workflow_manager.resume_workflow(workflow_id)
    if success:
        return JSONResponse({"success": True, "message": "Workflow resumed"})
    else:
        raise HTTPException(status_code=400, detail="Cannot resume workflow")


@router.get("/active")
async def get_active_workflows():
    """Get all active workflows"""
    workflows = workflow_manager.get_active_workflows()
    return JSONResponse({
        "workflows": [
            {
                "workflow_id": w["workflow_id"],
                "adaptation_id": w["adaptation_id"],
                "status": w["status"].value,
                "stage": w["stage"].value,
                "progress": w["progress"],
                "started_at": w["started_at"].isoformat() if w.get("started_at") else None
            }
            for w in workflows
        ]
    })