from __future__ import annotations

import argparse

from urbanvision_risk.app.api import create_app
from urbanvision_risk.app.service import LocalInspectionService
from urbanvision_risk.errors import ProjectError, report_error

LOOPBACK_HOSTS = frozenset({"127.0.0.1", "localhost", "::1"})


def validate_bind(host: str, port: int) -> tuple[str, int]:
    if host not in LOOPBACK_HOSTS:
        raise ProjectError(
            "E302",
            "本地应用只允许监听本机回环地址",
            "The local app only allows a local loopback host",
            "使用 127.0.0.1、localhost 或 ::1",
            "Use 127.0.0.1, localhost, or ::1",
            host,
        )
    if not 1 <= port <= 65535:
        raise ProjectError(
            "E302",
            "端口必须位于 1 到 65535",
            "Port must be between 1 and 65535",
            "使用例如 --port 8000",
            "Use a value such as --port 8000",
            str(port),
        )
    return host, port


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run the fully local inspection app / 运行完全本地巡检应用"
    )
    parser.add_argument("--run-name", required=True)
    parser.add_argument("--confidence", type=float, default=0.25)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--debug", action="store_true")
    args = parser.parse_args()
    try:
        host, port = validate_bind(args.host, args.port)
        service = LocalInspectionService(args.run_name, confidence=args.confidence)
        app = create_app(service)
    except ProjectError as error:
        return report_error(error, debug=args.debug)

    import uvicorn

    url_host = f"[{host}]" if ":" in host else host
    print(f"[PASS] 本地应用已就绪 / Local app ready: http://{url_host}:{port}")
    print("[INFO] 按 Control+C 停止 / Press Control+C to stop")
    uvicorn.run(app, host=host, port=port, log_level="info")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
