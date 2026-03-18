from __future__ import annotations

import io
import json
import os
import sys
from contextlib import redirect_stdout
from pathlib import Path

from .backend import _patch_ssl_if_needed
from .service import BridgeService


def main() -> int:
    _patch_ssl_if_needed()
    payload = json.loads(sys.stdin.read() or "{}")
    interface_name = payload["interface"]
    params = payload.get("params", {})
    max_bytes = int(payload.get("max_bytes", os.environ.get("AKSHARE_NODE_MAX_BYTES", "5000")))
    db_path = payload.get("db_path") or os.environ.get("AKSHARE_NODE_DB_PATH") or str(
        Path.cwd() / "data" / "akshare_cache.sqlite"
    )
    test_mode = str(os.environ.get("AKSHARE_NODE_TEST_MODE", "")).lower() in {"1", "true", "yes", "on"}

    service = BridgeService(db_path=db_path, max_bytes=max_bytes, test_mode=test_mode)

    try:
        with redirect_stdout(io.StringIO()):
            result = service.handle(interface_name=interface_name, params=params)
    except Exception as exc:
        sys.stdout.write(
            json.dumps(
                {
                    "ok": False,
                    "interface": interface_name,
                    "error": {"type": exc.__class__.__name__, "message": str(exc)},
                },
                ensure_ascii=False,
            )
        )
        return 1

    sys.stdout.write(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
