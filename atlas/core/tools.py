"""Tool decorator and schema generation for Atlas."""

from __future__ import annotations

import inspect
import types
from typing import Any, Union, get_args, get_origin, get_type_hints


def _type_to_schema(annotation: Any) -> dict[str, Any]:
    origin = get_origin(annotation)
    args = get_args(annotation)

    if origin is list or annotation is list:
        item_type = args[0] if args else Any
        return {"type": "array", "items": _type_to_schema(item_type)}

    if origin is dict or annotation is dict:
        return {"type": "object"}

    if origin is tuple or annotation is tuple:
        item_type = args[0] if args else Any
        return {"type": "array", "items": _type_to_schema(item_type)}

    if origin is None:
        return {"type": "string"}

    if origin is type(None):
        return {"type": "null"}

    if origin is type:
        return {"type": "string"}

    if origin is Union or origin is types.UnionType:
        non_none = [arg for arg in args if arg is not type(None)]  # noqa: E721
        if len(non_none) == 1:
            return _type_to_schema(non_none[0])
        return {"type": "string"}

    if annotation in (str,):
        return {"type": "string"}
    if annotation in (int,):
        return {"type": "integer"}
    if annotation in (float,):
        return {"type": "number"}
    if annotation in (bool,):
        return {"type": "boolean"}

    return {"type": "string"}


def build_tool_schema(fn: Any, name: str | None = None, description: str | None = None) -> dict[str, Any]:
    """Build OpenAI-compatible tool schema from a function signature."""
    signature = inspect.signature(fn)
    type_hints = get_type_hints(fn)

    properties: dict[str, Any] = {}
    required: list[str] = []

    for param_name, param in signature.parameters.items():
        if param.kind in (inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD):
            continue

        annotation = type_hints.get(param_name, Any)
        schema = _type_to_schema(annotation)
        properties[param_name] = schema

        if param.default is inspect.Parameter.empty:
            required.append(param_name)

    tool_name = name or fn.__name__
    tool_description = description or inspect.getdoc(fn) or ""

    return {
        "type": "function",
        "function": {
            "name": tool_name,
            "description": tool_description,
            "parameters": {
                "type": "object",
                "properties": properties,
                "required": required,
            },
        },
    }


def tool(_fn: Any | None = None, *, name: str | None = None, description: str | None = None):
    """Decorator that marks a function as an agent tool."""

    def decorator(fn):
        fn.__tool__ = True
        fn.__tool_schema__ = build_tool_schema(fn, name=name, description=description)
        return fn

    if _fn is None:
        return decorator

    return decorator(_fn)


def is_tool(fn: Any) -> bool:
    return bool(getattr(fn, "__tool__", False))


def get_tool_schema(fn: Any) -> dict[str, Any]:
    return getattr(fn, "__tool_schema__")
