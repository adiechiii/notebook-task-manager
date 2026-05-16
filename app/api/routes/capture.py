from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.schemas.capture_schema import (
    CaptureConfirmRequest,
    CaptureConfirmResponse,
    CapturePreviewRequest,
    CapturePreviewResponse,
)
from app.services.capture_confirm_service import confirm_capture
from app.services.capture_preview_service import preview_capture

router = APIRouter()


@router.post("/capture/preview", response_model=CapturePreviewResponse, operation_id="previewCapture")
def capture_preview(request: CapturePreviewRequest):
    return CapturePreviewResponse(
        **preview_capture(
            text=request.text,
            project=request.project,
            source_type=request.source_type,
            capture_source=request.capture_source,
        )
    )

@router.post("/capture/confirm", response_model=CaptureConfirmResponse, operation_id="confirmCapture")
def capture_confirm(request: CaptureConfirmRequest):
    result = confirm_capture(
        text=request.text,
        project=request.project,
        recommended_type=request.recommended_type,
        source_type=request.source_type,
        capture_source=request.capture_source,
        confirmation=request.confirmation,
    )

    if not result["confirmed"]:
        return JSONResponse(status_code=400, content=result)

    return CaptureConfirmResponse(**result)

