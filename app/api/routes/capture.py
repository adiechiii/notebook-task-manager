from fastapi import APIRouter

from app.schemas.capture_schema import CapturePreviewRequest, CapturePreviewResponse
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
