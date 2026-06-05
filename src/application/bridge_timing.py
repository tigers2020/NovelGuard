from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from typing import Any

_LOGGER = logging.getLogger(__name__)


@dataclass
class BridgeTimingSpan:
    method: str
    t0: float = field(default_factory=time.perf_counter)
    fields: dict[str, Any] = field(default_factory=dict)

    def finish(self, *, ok: bool, error_code: str | None = None) -> None:
        elapsed_ms = int((time.perf_counter() - self.t0) * 1000)
        payload = {
            "event": "bridge_timing",
            "method": self.method,
            "elapsed_ms": elapsed_ms,
            "ok": ok,
            "error_code": error_code,
            **self.fields,
        }
        _LOGGER.debug("%s", json.dumps(payload, ensure_ascii=False))


def bridge_method_span(method: str, **fields: Any) -> BridgeTimingSpan:
    return BridgeTimingSpan(method=method, fields=fields)
