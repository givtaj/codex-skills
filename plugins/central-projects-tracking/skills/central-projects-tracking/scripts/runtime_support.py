#!/usr/bin/env python3
"""Shared deterministic runtime preflight for tracking entry points."""

from __future__ import annotations

import json
import sys
from typing import Any, TextIO


MINIMUM_PYTHON = (3, 10)


def require_supported_python(
    version_info: Any = None,
    stream: TextIO | None = None,
) -> bool:
    """Report one bounded machine-readable error when Python is too old."""
    observed = sys.version_info if version_info is None else version_info
    if tuple(observed[:2]) >= MINIMUM_PYTHON:
        return True
    output = sys.stderr if stream is None else stream
    print(
        json.dumps(
            {
                "status": "failed",
                "reason": "unsupported_python",
                "required": "3.10+",
            },
            separators=(",", ":"),
        ),
        file=output,
    )
    return False
