from __future__ import annotations

import json
import os
import tempfile
import time
import unittest
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path


BASE_URL = "http://127.0.0.1:8888"
PAYLOAD_TEMPLATE = {
    "interface": "futures_zh_hist",
    "params": {
        "symbol": "SH2605",
        "period": "daily",
        "start_date": "2026-02-18",
        "end_date": "2026-03-18",
    },
    "verify_ssl": False,
    "max_bytes": 5000,
}


def _healthcheck() -> bool:
    try:
        with urllib.request.urlopen(f"{BASE_URL}/health", timeout=3) as resp:
            body = json.loads(resp.read().decode("utf-8"))
        return body.get("ok") is True
    except Exception:
        return False


class RealApiConcurrencyBenchmarkTest(unittest.TestCase):
    @unittest.skipUnless(os.environ.get("RUN_REAL_API_BENCH") == "1", "set RUN_REAL_API_BENCH=1 to run real API benchmark")
    @unittest.skipUnless(_healthcheck(), "local API server is not running on 127.0.0.1:8888")
    def test_real_api_concurrency_benchmark(self) -> None:
        results = [self._run_batch(concurrency) for concurrency in (1, 2, 3)]
        print(json.dumps(results, ensure_ascii=False, indent=2))

        for batch in results:
            self.assertTrue(all(item["ok"] for item in batch["requests"]), batch)

    def _run_batch(self, concurrency: int) -> dict[str, object]:
        db_path = str(Path(tempfile.gettempdir()) / f"akshare_real_bench_{concurrency}_{int(time.time() * 1000)}.sqlite")
        payload = dict(PAYLOAD_TEMPLATE)
        payload["params"] = dict(PAYLOAD_TEMPLATE["params"])
        payload["db_path"] = db_path

        def invoke(idx: int) -> dict[str, object]:
            req = urllib.request.Request(
                f"{BASE_URL}/invoke",
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"},
            )
            started = time.perf_counter()
            try:
                with urllib.request.urlopen(req, timeout=240) as resp:
                    body = json.loads(resp.read().decode("utf-8"))
                return {
                    "idx": idx,
                    "ok": body.get("ok", False),
                    "elapsed_s": round(time.perf_counter() - started, 3),
                    "returned_rows": body.get("returned_rows"),
                    "cache_hit": body.get("cache_hit"),
                }
            except urllib.error.HTTPError as exc:
                body = json.loads(exc.read().decode("utf-8"))
                return {
                    "idx": idx,
                    "ok": False,
                    "elapsed_s": round(time.perf_counter() - started, 3),
                    "error": body,
                }

        batch_started = time.perf_counter()
        with ThreadPoolExecutor(max_workers=concurrency) as executor:
            requests = list(executor.map(invoke, range(concurrency)))

        return {
            "concurrency": concurrency,
            "wall_s": round(time.perf_counter() - batch_started, 3),
            "requests": requests,
        }


if __name__ == "__main__":
    unittest.main(verbosity=2)
