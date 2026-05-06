# SPDX-License-Identifier: Apache-2.0
"""Process-wide modifier configuration.

The modifier config is a singleton mutated by /__test__/configure and read by
the various middlewares and endpoints. Tasks set their desired failure-mode
combinations at reset time; nothing else in the codebase needs to know about
specific failure modes.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ModifierConfig:
    # LatencyMiddleware
    latency_profile: str = "fast"  # fast | realistic | slow_3g | none

    # PaymentOutcomeMiddleware
    # Either a single outcome string or a list/sequence consumed in order.
    # Outcome values: success | declined | timeout | 3ds_required
    payment_outcome: Any = "success"
    _payment_cursor: int = 0

    # ServerErrorRateMiddleware
    server_error_rate: float = 0.0
    server_error_paths: list[str] = field(default_factory=lambda: ["/api/products"])

    # SessionTTLMiddleware
    # When set, overrides the default session TTL (seconds).
    session_ttl_s: int | None = None

    # Time-freeze (consumed by checkout/coupon expiry checks)
    frozen_time_iso: str | None = None

    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    def reset(self) -> None:
        with self._lock:
            self.latency_profile = "fast"
            self.payment_outcome = "success"
            self._payment_cursor = 0
            self.server_error_rate = 0.0
            self.server_error_paths = ["/api/products"]
            self.session_ttl_s = None
            self.frozen_time_iso = None

    def update(self, payload: dict[str, Any]) -> None:
        """Apply a partial config update from /__test__/configure."""
        with self._lock:
            if "latency_profile" in payload:
                self.latency_profile = payload["latency_profile"] or "fast"
            if "payment_outcome" in payload:
                self.payment_outcome = payload["payment_outcome"]
                self._payment_cursor = 0
            if "server_error_rate" in payload:
                self.server_error_rate = float(payload["server_error_rate"] or 0.0)
            if "server_error_paths" in payload:
                self.server_error_paths = list(payload["server_error_paths"] or [])
            if "session_ttl_s" in payload:
                self.session_ttl_s = payload["session_ttl_s"]
            if "frozen_time_iso" in payload:
                self.frozen_time_iso = payload["frozen_time_iso"]

    def next_payment_outcome(self) -> str:
        """Return the next payment outcome.

        Supports three shapes:
        - "success" / "declined" / ... — fixed outcome, returned on every call
        - {"sequence": [...]} — consumed in order, last value sticks
        - [...] — same as sequence
        """
        with self._lock:
            value = self.payment_outcome
            if isinstance(value, dict) and "sequence" in value:
                seq = value["sequence"]
            elif isinstance(value, list):
                seq = value
            else:
                return str(value)

            idx = min(self._payment_cursor, len(seq) - 1)
            self._payment_cursor += 1
            return str(seq[idx])

    def to_dict(self) -> dict[str, Any]:
        with self._lock:
            return {
                "latency_profile": self.latency_profile,
                "payment_outcome": self.payment_outcome,
                "server_error_rate": self.server_error_rate,
                "server_error_paths": list(self.server_error_paths),
                "session_ttl_s": self.session_ttl_s,
                "frozen_time_iso": self.frozen_time_iso,
            }


_config = ModifierConfig()


def get_config() -> ModifierConfig:
    return _config


# ---------------------------------------------------------------------------
# Latency profile helpers
# ---------------------------------------------------------------------------

LATENCY_PROFILES: dict[str, dict[str, tuple[float, float]]] = {
    "none": {"default": (0.0, 0.0)},
    "fast": {"default": (0.005, 0.012)},
    "realistic": {
        "default": (0.04, 0.12),
        "/api/checkout": (0.10, 0.25),
        "/api/products/search": (0.06, 0.18),
    },
    "slow_3g": {
        "default": (0.4, 1.2),
        "/api/checkout": (0.8, 2.0),
    },
}


def latency_for_path(profile: str, path: str) -> tuple[float, float]:
    """Returns (min, max) seconds to sleep for this profile/path."""
    bucket = LATENCY_PROFILES.get(profile) or LATENCY_PROFILES["fast"]
    for prefix, value in bucket.items():
        if prefix == "default":
            continue
        if path.startswith(prefix):
            return value
    return bucket.get("default", (0.0, 0.0))
