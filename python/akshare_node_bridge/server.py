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
        try:
            if self.path == "/health":
                self._write_json_safe(HTTPStatus.OK, {"ok": True, "host": HOST, "port": PORT})
                return
            if self.path == "/tools":
                self._write_json_safe(HTTPStatus.OK, {"ok": True, "tools": sorted(SUPPORTED_INTERFACES)})
                return
            self._write_json_safe(HTTPStatus.NOT_FOUND, {"ok": False, "error": "Not found"})
        except Exception:
            self._safe_write_error()

    def do_POST(self) -> None:  # noqa: N802
        if self.path != "/invoke":
            self._write_json_safe(HTTPStatus.NOT_FOUND, {"ok": False, "error": "Not found"})
            return

        try:
            payload = self._read_json() or {}
            if not isinstance(payload, dict):
                self._write_json_safe(HTTPStatus.BAD_REQUEST, {
                    "ok": False,
                    "error": {"type": "BadRequest", "message": "请求体须为 JSON 对象"}
                })
                return
            interface_name = payload.get("interface")
            if not interface_name:
                self._write_json_safe(HTTPStatus.BAD_REQUEST, {
                    "ok": False,
                    "error": {"type": "BadRequest", "message": "缺少 interface 字段，请指定接口名如 stock_zh_a_spot"}
                })
                return
            interface_name = str(interface_name).strip() if interface_name is not None else ""
            if not interface_name:
                self._write_json_safe(HTTPStatus.BAD_REQUEST, {
                    "ok": False,
                    "error": {"type": "BadRequest", "message": "interface 须为非空字符串"}
                })
                return
            params = payload.get("params")
            if params is not None and not isinstance(params, dict):
                params = {}
            params = params or {}
            if not bool(payload.get("verify_ssl", True)):
                _patch_ssl_if_needed(force=True)
            service = build_service(
                max_bytes=payload.get("max_bytes"),
                db_path=payload.get("db_path"),
            )
            result = service.handle(interface_name=interface_name, params=params)
            self._write_json_safe(HTTPStatus.OK, result)
        except Exception as exc:
            try:
                err_msg = str(exc)
                self._write_json_safe(
                    HTTPStatus.BAD_REQUEST,
                    {
                        "ok": False,
                        "error": {
                            "type": exc.__class__.__name__,
                            "message": err_msg,
                            "hint": "请检查 params 是否包含必填参数，格式是否正确" if "需要参数" in err_msg else None,
                        },
                    },
                )
            except Exception:
                self._safe_write_error()

    def log_message(self, format: str, *args: Any) -> None:  # noqa: A003
        return

    def _write_json_safe(self, status: HTTPStatus, payload: dict[str, Any]) -> None:
        """写入 JSON 响应，捕获所有异常避免服务崩溃。"""
        try:
            self._write_json(status, payload)
        except Exception:
            pass

    def _safe_write_error(self) -> None:
        """兜底：尝试发送 500 错误，失败则静默。"""
        try:
            self._write_json(
                HTTPStatus.INTERNAL_SERVER_ERROR,
                {"ok": False, "error": "internal error"},
            )
        except Exception:
            pass

    def _read_json(self) -> dict[str, Any]:
        content_length = int(self.headers.get("Content-Length", "0"))
        raw_body = self.rfile.read(content_length)
        if not raw_body:
            return {}
        return json.loads(raw_body.decode("utf-8"))

    def _write_json(self, status: HTTPStatus, payload: dict[str, Any]) -> None:
        body = json.dumps(payload, ensure_ascii=False, allow_nan=False).encode("utf-8")
        try:
            self.send_response(status.value)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        except OSError:
            # 客户端断开或网络异常时静默忽略，避免堆栈输出导致服务看似崩溃
            pass


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

