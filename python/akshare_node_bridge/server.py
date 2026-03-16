from __future__ import annotations

import json
import os
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from .backend import _patch_ssl_if_needed
from .service import SUPPORTED_INTERFACES, BridgeService


HOST = "127.0.0.1"
PORT = 8888


def build_service(max_bytes: int | None = None, db_path: str | None = None) -> BridgeService:
    resolved_max_bytes = int(max_bytes or os.environ.get("AKSHARE_NODE_MAX_BYTES", "2000"))
    resolved_db_path = db_path or os.environ.get("AKSHARE_NODE_DB_PATH") or str(
        Path.cwd() / "data" / "akshare_cache.sqlite"
    )
    test_mode = str(os.environ.get("AKSHARE_NODE_TEST_MODE", "")).lower() in {"1", "true", "yes", "on"}
    return BridgeService(db_path=resolved_db_path, max_bytes=resolved_max_bytes, test_mode=test_mode)


class AkshareRequestHandler(BaseHTTPRequestHandler):
    server_version = "AkshareNodeHTTP/0.1"

    def do_GET(self) -> None:  # noqa: N802
        if self.path == "/health":
            self._write_json(
                HTTPStatus.OK,
                {"ok": True, "host": HOST, "port": PORT},
            )
            return
        if self.path == "/tools":
            self._write_json(
                HTTPStatus.OK,
                {"ok": True, "tools": sorted(SUPPORTED_INTERFACES)},
            )
            return
        self._write_json(HTTPStatus.NOT_FOUND, {"ok": False, "error": "Not found"})

    def do_POST(self) -> None:  # noqa: N802
        if self.path != "/invoke":
            self._write_json(HTTPStatus.NOT_FOUND, {"ok": False, "error": "Not found"})
            return

        try:
            payload = self._read_json()
            interface_name = payload["interface"]
            params = payload.get("params", {})
            # If the caller requests no SSL verification, apply the patch now
            # (idempotent – safe to call multiple times).
            if not bool(payload.get("verify_ssl", True)):
                _patch_ssl_if_needed(force=True)
            service = build_service(
                max_bytes=payload.get("max_bytes"),
                db_path=payload.get("db_path"),
            )
            result = service.handle(interface_name=interface_name, params=params)
        except Exception as exc:
            self._write_json(
                HTTPStatus.BAD_REQUEST,
                {
                    "ok": False,
                    "error": {
                        "type": exc.__class__.__name__,
                        "message": str(exc),
                    },
                },
            )
            return

        self._write_json(HTTPStatus.OK, result)

    def log_message(self, format: str, *args: Any) -> None:  # noqa: A003
        return

    def _read_json(self) -> dict[str, Any]:
        content_length = int(self.headers.get("Content-Length", "0"))
        raw_body = self.rfile.read(content_length)
        if not raw_body:
            return {}
        return json.loads(raw_body.decode("utf-8"))

    def _write_json(self, status: HTTPStatus, payload: dict[str, Any]) -> None:
        body = json.dumps(payload, ensure_ascii=False, allow_nan=False).encode("utf-8")
        self.send_response(status.value)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def main() -> int:
    # 不在启动时 patch SSL，由请求 verify_ssl 或 backend 按 env 处理
    httpd = ThreadingHTTPServer((HOST, PORT), AkshareRequestHandler)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:  # pragma: no cover
        pass
    finally:
        httpd.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

