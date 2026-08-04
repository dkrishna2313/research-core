"""
Serialization utilities for research-core contracts.

serialize() converts any contract dataclass (or scalar value) to a
plain Python structure that is safe to pass to json.dumps().

Conversion rules:
- dataclass      → dict of field_name: serialize(value)
- Enum           → .value (always a str for our str-Enum types)
- datetime       → ISO 8601 string with timezone offset
- MappingProxyType / dict → dict with serialized values
- tuple / list   → list with serialized elements
- None, bool, int, float, str → unchanged
- date           → ISO 8601 date string

Unknown types are left as-is; callers that need strict JSON must handle
them separately (e.g. by passing through json.dumps with a default hook).
"""

from __future__ import annotations

import dataclasses
import types
from datetime import date, datetime
from enum import Enum
from typing import Any


def serialize(obj: Any) -> Any:
    """Recursively convert a contract object to a JSON-serializable structure."""
    if obj is None or isinstance(obj, (bool, int, float, str)):
        return obj

    if isinstance(obj, Enum):
        return obj.value

    if isinstance(obj, datetime):
        return obj.isoformat()

    if isinstance(obj, date):
        return obj.isoformat()

    if isinstance(obj, (types.MappingProxyType, dict)):
        return {str(k): serialize(v) for k, v in obj.items()}

    if isinstance(obj, (tuple, list)):
        return [serialize(item) for item in obj]

    if dataclasses.is_dataclass(obj) and not isinstance(obj, type):
        return {
            f.name: serialize(getattr(obj, f.name))
            for f in dataclasses.fields(obj)
        }

    return obj
