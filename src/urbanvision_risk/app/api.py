from __future__ import annotations

from typing import Annotated

from fastapi import FastAPI, File, Query, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.requests import Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, Response
from starlette.middleware.base import RequestResponseEndpoint

from urbanvision_risk.app.service import MAX_UPLOAD_BYTES, LocalInspectionService
from urbanvision_risk.app.web import APP_HTML
from urbanvision_risk.errors import ProjectError


def _error_payload(error: ProjectError) -> dict[str, object]:
    return {
        "error": {
            "code": error.code,
            "message_zh": error.message_zh,
            "message_en": error.message_en,
            "recovery_zh": error.recovery_zh,
            "recovery_en": error.recovery_en,
            "context": error.context,
        }
    }


def _status_code(error: ProjectError) -> int:
    return {
        "E201": 404,
        "E204": 409,
        "E301": 500,
        "E302": 422,
        "E601": 400,
        "E602": 500,
    }.get(error.code, 500)


def create_app(service: LocalInspectionService) -> FastAPI:
    app = FastAPI(
        title="UrbanVision-Risk Local API",
        version="2.0.0",
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )
    app.state.inspection_service = service

    @app.middleware("http")
    async def security_headers(request: Request, call_next: RequestResponseEndpoint) -> Response:
        response = await call_next(request)
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; img-src 'self' blob: data:; "
            "style-src 'self' 'unsafe-inline'; script-src 'self' 'unsafe-inline'; "
            "connect-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'"
        )
        return response

    @app.exception_handler(ProjectError)
    async def project_error_handler(_: Request, error: ProjectError) -> JSONResponse:
        return JSONResponse(_error_payload(error), status_code=_status_code(error))

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(_: Request, error: RequestValidationError) -> JSONResponse:
        project_error = ProjectError(
            "E601",
            "请求中缺少有效的图片文件",
            "The request is missing a valid image file",
            "使用名为 image 的字段上传一张 JPEG、PNG 或 WebP",
            "Upload one JPEG, PNG, or WebP in a field named image",
            str(error.errors()),
        )
        return JSONResponse(_error_payload(project_error), status_code=422)

    @app.get("/", response_class=HTMLResponse)
    async def home() -> HTMLResponse:
        return HTMLResponse(APP_HTML)

    @app.get("/favicon.ico", include_in_schema=False)
    async def favicon() -> Response:
        return Response(status_code=204)

    @app.get("/api/health")
    async def health() -> dict[str, object]:
        return service.health_payload()

    @app.get("/api/review-queue")
    async def review_queue(
        limit: Annotated[int, Query(ge=1, le=500)] = 50,
    ) -> dict[str, object]:
        return service.review_queue(limit=limit)

    @app.post("/api/inspect")
    async def inspect(
        image: Annotated[UploadFile, File(description="One local road image")],
    ) -> dict[str, object]:
        content = await image.read(MAX_UPLOAD_BYTES + 1)
        await image.close()
        return service.inspect_bytes(
            content,
            filename=image.filename,
            content_type=image.content_type or "",
        )

    @app.get("/api/inspections/{inspection_id}/annotated.jpg")
    async def annotated_image(inspection_id: str) -> FileResponse:
        return FileResponse(
            service.annotated_path(inspection_id),
            media_type="image/jpeg",
            filename=f"{inspection_id}-annotated.jpg",
        )

    @app.post("/api/inspections/{inspection_id}/narrative")
    async def narrative(inspection_id: str) -> dict[str, object]:
        return service.narrative(inspection_id)

    return app
