"""Shared test fixtures and module-level stubs.

The ``workers`` module only exists inside Pyodide on Cloudflare Workers.
We inject a minimal fake before any test can import ``worker.py`` so the
import does not fail in a normal Python environment.
"""

from __future__ import annotations

import json
import sys
import types


def _install_fake_workers() -> None:
    if "workers" in sys.modules:
        return

    mod = types.ModuleType("workers")

    class Response:
        def __init__(self, body: str = "", status: int = 200) -> None:
            self.body = body
            self.status = status

        @classmethod
        def json(cls, obj: object) -> Response:
            return cls(json.dumps(obj))

    class WorkerEntrypoint:
        def __init__(self, env: object = None) -> None:
            self.env = env

    mod.Response = Response  # type: ignore[attr-defined]
    mod.WorkerEntrypoint = WorkerEntrypoint  # type: ignore[attr-defined]
    sys.modules["workers"] = mod


_install_fake_workers()
