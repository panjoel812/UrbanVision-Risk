from __future__ import annotations

from typing import Annotated

from fastapi import FastAPI, File, Form, Query, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.requests import Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, Response
from starlette.middleware.base import RequestResponseEndpoint

from urbanvision_risk.app.metrology_service import (
    MAX_METROLOGY_UPLOAD_BYTES,
    LocalMetrologyService,
)
from urbanvision_risk.app.metrology_web import METROLOGY_HTML
from urbanvision_risk.app.service import MAX_UPLOAD_BYTES, LocalInspectionService
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
        "E603": 409,
        "E501": 422,
        "E502": 422,
        "E503": 400,
        "E504": 500,
        "E505": 422,
        "E506": 422,
    }.get(error.code, 500)


def create_app(
    service: LocalInspectionService,
    metrology_service: LocalMetrologyService | None = None,
) -> FastAPI:
    active_metrology = metrology_service or LocalMetrologyService(
        paths=getattr(service, "paths", None)
    )
    app = FastAPI(
        title="UrbanVision-Risk Local API",
        version="4.6.0",
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )
    app.state.inspection_service = service
    app.state.metrology_service = active_metrology

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
    async def validation_error_handler(
        request: Request, error: RequestValidationError
    ) -> JSONResponse:
        if request.url.path.startswith("/api/metrology"):
            project_error = ProjectError(
                "E506",
                "量测请求缺少必要字段或字段格式错误",
                "The metrology request is missing a field or contains an invalid value",
                "检查原图、PNG 掩膜、标定模式和数值字段",
                "Check the source, PNG mask, calibration mode, and numeric fields",
                str(error.errors()),
            )
        else:
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
        return HTMLResponse(METROLOGY_HTML)

    @app.get("/metrology", response_class=HTMLResponse)
    async def metrology_home() -> HTMLResponse:
        """Compatibility alias for saved v4.0 bookmarks / 兼容旧书签。"""
        return HTMLResponse(METROLOGY_HTML)

    @app.get("/favicon.ico", include_in_schema=False)
    async def favicon() -> Response:
        return Response(status_code=204)

    @app.get("/api/health")
    async def health() -> dict[str, object]:
        payload = service.health_payload()
        payload["precision_metrology"] = True
        payload["metrology_modes"] = ["pixel", "manual", "aruco"]
        payload["automatic_pixel_draft"] = True
        payload["ranked_hotspot_review"] = True
        payload["synchronized_review_loupe"] = True
        payload["auditable_hotspot_dispositions"] = True
        return payload

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

    @app.post("/api/metrology/demo")
    async def metrology_demo() -> dict[str, object]:
        return active_metrology.demo()

    @app.post("/api/metrology/proposals")
    async def metrology_proposal(
        image: Annotated[UploadFile, File(description="One local road image")],
        sensitivity: Annotated[float, Form()] = 0.55,
    ) -> dict[str, object]:
        source_content = await image.read(MAX_METROLOGY_UPLOAD_BYTES + 1)
        await image.close()
        return active_metrology.propose_mask_bytes(
            source_content=source_content,
            source_filename=image.filename,
            source_content_type=image.content_type or "",
            sensitivity=sensitivity,
        )

    @app.get("/api/metrology/proposals/{proposal_id}/{artifact_name}")
    async def metrology_proposal_artifact(
        proposal_id: str,
        artifact_name: str,
    ) -> FileResponse:
        path = active_metrology.proposal_artifact_path(
            proposal_id,
            artifact_name,
        )
        media_type = "application/json" if artifact_name == "evidence.json" else "image/png"
        return FileResponse(
            path,
            media_type=media_type,
            filename=path.name,
        )

    @app.post("/api/metrology/analyze")
    async def metrology_analyze(
        image: Annotated[UploadFile, File(description="One local road image")],
        mask: Annotated[UploadFile, File(description="A same-size binary PNG mask")],
        calibration_mode: Annotated[str, Form()],
        manual_points: Annotated[str | None, Form()] = None,
        physical_width: Annotated[float | None, Form()] = None,
        physical_height: Annotated[float | None, Form()] = None,
        unit: Annotated[str | None, Form()] = None,
        pixels_per_unit: Annotated[float | None, Form()] = None,
        point_sigma_pixels: Annotated[float | None, Form()] = None,
        uncertainty_samples: Annotated[int, Form()] = 64,
        segmentation_radius_pixels: Annotated[int, Form()] = 1,
        proposal_id: Annotated[str | None, Form()] = None,
        review_state: Annotated[str, Form()] = "human_reviewed",
        reviewed_hotspots: Annotated[str | None, Form()] = None,
        hotspot_decisions: Annotated[str | None, Form()] = None,
    ) -> dict[str, object]:
        source_content = await image.read(MAX_METROLOGY_UPLOAD_BYTES + 1)
        mask_content = await mask.read(MAX_METROLOGY_UPLOAD_BYTES + 1)
        await image.close()
        await mask.close()
        return active_metrology.analyze_bytes(
            source_content=source_content,
            source_filename=image.filename,
            source_content_type=image.content_type or "",
            mask_content=mask_content,
            mask_filename=mask.filename,
            mask_content_type=mask.content_type or "",
            calibration_mode=calibration_mode,
            manual_points=manual_points,
            physical_width=physical_width,
            physical_height=physical_height,
            unit=unit,
            pixels_per_unit=pixels_per_unit,
            point_sigma_pixels=point_sigma_pixels,
            uncertainty_samples=uncertainty_samples,
            segmentation_radius_pixels=segmentation_radius_pixels,
            proposal_id=proposal_id,
            review_state=review_state,
            reviewed_hotspots=reviewed_hotspots,
            hotspot_decisions=hotspot_decisions,
        )

    @app.get("/api/metrology/runs")
    async def metrology_runs(
        limit: Annotated[int, Query(ge=1, le=100)] = 50,
    ) -> dict[str, object]:
        return active_metrology.list_runs(limit=limit)

    @app.post("/api/metrology/runs/{run_id}/maintenance-plan")
    async def metrology_maintenance_plan(
        run_id: str,
        route_width_mm: Annotated[float, Form()],
        route_depth_mm: Annotated[float, Form()],
        waste_percent: Annotated[float, Form()],
        unit_cost_per_liter: Annotated[float | None, Form()] = None,
    ) -> dict[str, object]:
        return active_metrology.create_maintenance_plan(
            run_id,
            route_width_mm=route_width_mm,
            route_depth_mm=route_depth_mm,
            waste_percent=waste_percent,
            unit_cost_per_liter=unit_cost_per_liter,
        )

    @app.get("/api/metrology/runs/{run_id}/plans/{plan_id}.json")
    async def metrology_plan(run_id: str, plan_id: str) -> FileResponse:
        path = active_metrology.plan_path(run_id, plan_id)
        return FileResponse(
            path,
            media_type="application/json",
            filename=path.name,
        )

    @app.post("/api/metrology/compare")
    async def metrology_compare(
        baseline_run_id: Annotated[str, Form()],
        current_run_id: Annotated[str, Form()],
        elapsed_days: Annotated[float, Form()],
        length_review_threshold_percent: Annotated[float, Form()] = 10.0,
        width_review_threshold_percent: Annotated[float, Form()] = 10.0,
        match_tolerance_mm: Annotated[float, Form()] = 5.0,
    ) -> dict[str, object]:
        return active_metrology.compare_runs(
            baseline_run_id=baseline_run_id,
            current_run_id=current_run_id,
            elapsed_days=elapsed_days,
            length_review_threshold_percent=length_review_threshold_percent,
            width_review_threshold_percent=width_review_threshold_percent,
            match_tolerance_mm=match_tolerance_mm,
        )

    @app.get("/api/metrology/comparisons/{comparison_id}.json")
    async def metrology_comparison(comparison_id: str) -> FileResponse:
        path = active_metrology.comparison_path(comparison_id)
        return FileResponse(
            path,
            media_type="application/json",
            filename=path.name,
        )

    @app.get("/api/metrology/comparisons/{comparison_id}/{artifact_name}")
    async def metrology_comparison_artifact(
        comparison_id: str,
        artifact_name: str,
    ) -> FileResponse:
        path = active_metrology.comparison_artifact_path(
            comparison_id,
            artifact_name,
        )
        return FileResponse(
            path,
            media_type="image/png",
            filename=path.name,
        )

    @app.get("/api/metrology/runs/{run_id}/{artifact_name}")
    async def metrology_artifact(run_id: str, artifact_name: str) -> FileResponse:
        path = active_metrology.artifact_path(run_id, artifact_name)
        media_type = {
            ".jpg": "image/jpeg",
            ".png": "image/png",
            ".json": "application/json",
        }.get(path.suffix.lower(), "application/octet-stream")
        return FileResponse(path, media_type=media_type, filename=path.name)

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
