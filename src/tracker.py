from __future__ import annotations

import logging
import os
import time

logger = logging.getLogger(__name__)

_MLFLOW_ENABLED: bool = bool(os.environ.get("MLFLOW_TRACKING_URI", "").strip())


class QueryTracker:
    """
    One instance per request. Wraps a single MLflow run.
    All methods are no-ops when MLFLOW_TRACKING_URI is unset — mlflow is never imported.
    finish() is idempotent: safe to call multiple times.
    """

    def __init__(self) -> None:
        self._active = _MLFLOW_ENABLED
        self._run = None
        self._start_time: float = 0.0
        self._tool_counts: dict[str, int] = {}
        self._token_chars: int = 0
        self._error: int = 0
        if self._active:
            import mlflow as _mlflow  # deferred — not loaded when tracking is disabled
            self._mlflow = _mlflow

    def start(self, user_id: str, query: str) -> None:
        if not self._active:
            return
        self._start_time = time.monotonic()
        self._mlflow.set_experiment("excelsis-agent")
        self._run = self._mlflow.start_run()
        self._mlflow.set_tag("user_id", user_id)
        self._mlflow.log_params({
            "model":       os.environ.get("MODEL", "qwen2.5:14b"),
            "embed_model": os.environ.get("EMBED_MODEL", "BAAI/bge-small-en-v1.5"),
            "temperature": "0.1",
            "num_ctx":     "8192",
        })

    def record_tool(self, tool_name: str) -> None:
        if not self._active:
            return
        self._tool_counts[tool_name] = self._tool_counts.get(tool_name, 0) + 1

    def record_tokens(self, char_count: int) -> None:
        if not self._active:
            return
        self._token_chars += char_count

    def record_error(self) -> None:
        if not self._active:
            return
        self._error = 1

    def finish(self) -> None:
        if not self._active or self._run is None:
            return
        try:
            elapsed_ms = (time.monotonic() - self._start_time) * 1000
            self._mlflow.log_metrics({
                "query_latency_ms": elapsed_ms,
                "tool_count":       float(sum(self._tool_counts.values())),
                "tokens_estimated": float(self._token_chars // 4),
                "error":            float(self._error),
            })
            for name, count in self._tool_counts.items():
                self._mlflow.log_metric(f"tool_{name.replace('-', '_')}", float(count))
            self._mlflow.end_run()
        except Exception:
            logger.warning("MLflow tracking failed", exc_info=True)
        finally:
            self._run = None  # ensures second call is always a no-op


def log_startup_config() -> None:
    """Log model config as a one-shot startup run. No-op if MLFLOW_TRACKING_URI is unset."""
    if not _MLFLOW_ENABLED:
        return
    import mlflow
    mlflow.set_experiment("excelsis-agent")
    with mlflow.start_run(run_name="startup"):
        mlflow.log_params({
            "model":       os.environ.get("MODEL", "qwen2.5:14b"),
            "embed_model": os.environ.get("EMBED_MODEL", "BAAI/bge-small-en-v1.5"),
        })
        mlflow.set_tag("event", "startup")
