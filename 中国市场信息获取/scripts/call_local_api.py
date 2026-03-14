#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Any


DEFAULT_BASE_URL = "http://127.0.0.1:8888"
DEFAULT_MAX_INLINE_BYTES = 5000


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="调用本地 AKShare HTTP 服务。")
    parser.add_argument("--interface", help="要调用的接口名。")
    parser.add_argument("--params", default="{}", help="接口参数，JSON 字符串。")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL, help="服务基础地址。")
    parser.add_argument("--health-check", action="store_true", help="调用 /health。")
    parser.add_argument("--list-tools", action="store_true", help="调用 /tools。")
    parser.add_argument(
        "--max-inline-bytes",
        type=int,
        default=DEFAULT_MAX_INLINE_BYTES,
        help="当 JSON 结果超过该字节数时写入文件。",
    )
    parser.add_argument(
        "--output-dir",
        default=str(Path.cwd() / "outputs"),
        help="需要写文件时使用的输出目录。",
    )
    args = parser.parse_args()
    if not args.health_check and not args.list_tools and not args.interface:
        parser.error("--interface is required unless --health-check or --list-tools is used")
    return args


def get_json(url: str) -> dict[str, Any]:
    request = urllib.request.Request(url, method="GET")
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {exc.code}: {body}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Failed to reach {url}: {exc}") from exc


def post_json(url: str, payload: dict[str, Any]) -> dict[str, Any]:
    request = urllib.request.Request(
        url,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json; charset=utf-8"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {exc.code}: {body}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Failed to reach {url}: {exc}") from exc


def write_output_file(output_dir: Path, interface_name: str, payload_bytes: bytes) -> Path:
    resolved_output_dir = output_dir.expanduser().resolve()
    resolved_output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    file_path = resolved_output_dir / f"{interface_name}-{timestamp}.json"
    file_path.write_bytes(payload_bytes)
    return file_path


def main() -> int:
    args = parse_args()
    base_url = args.base_url.rstrip("/")

    if args.health_check:
        sys.stdout.write(json.dumps(get_json(f"{base_url}/health"), ensure_ascii=False))
        return 0

    if args.list_tools:
        sys.stdout.write(json.dumps(get_json(f"{base_url}/tools"), ensure_ascii=False))
        return 0

    params = json.loads(args.params)
    result = post_json(f"{base_url}/invoke", {"interface": args.interface, "params": params})
    payload_bytes = json.dumps(result, ensure_ascii=False, allow_nan=False, indent=2).encode("utf-8")

    if len(payload_bytes) > args.max_inline_bytes:
        file_path = write_output_file(Path(args.output_dir), args.interface, payload_bytes)
        sys.stdout.write(
            json.dumps(
                {
                    "ok": True,
                    "stored_in_file": True,
                    "file_path": str(file_path),
                    "bytes": len(payload_bytes),
                    "interface": args.interface,
                },
                ensure_ascii=False,
            )
        )
        return 0

    sys.stdout.write(
        json.dumps(
            {
                "ok": True,
                "stored_in_file": False,
                "bytes": len(payload_bytes),
                "result": result,
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
