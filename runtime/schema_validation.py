"""Small, explicit JSON Schema subset used by the stdlib-only validator.

Unsupported keywords are configuration errors, never silently ignored. This
is deliberately limited to the keywords used by adjudication.schema.json.
"""

from __future__ import annotations

import re

KEYWORDS = {
    "$schema", "$id", "title", "description", "type", "required",
    "properties", "additionalProperties", "enum", "minLength", "pattern",
    "minItems", "items",
}
TYPES = {"object", "array", "string", "boolean", "integer", "number", "null"}


def check_schema(schema: object, at: str = "schema") -> list[str]:
    if not isinstance(schema, dict):
        return [f"{at} must be a schema object"]
    errors = [f"{at}: unsupported schema keyword {key!r}" for key in schema if key not in KEYWORDS]
    if "type" in schema and (not isinstance(schema["type"], str) or schema["type"] not in TYPES):
        errors.append(f"{at}: unsupported schema type {schema['type']!r}")
    if "additionalProperties" in schema and type(schema["additionalProperties"]) is not bool:
        errors.append(f"{at}: additionalProperties must be boolean")
    for keyword in ("minItems", "minLength"):
        if keyword in schema and (type(schema[keyword]) is not int or schema[keyword] < 0):
            errors.append(f"{at}: {keyword} must be a non-negative integer")
    if "required" in schema and (
        not isinstance(schema["required"], list)
        or not all(isinstance(key, str) for key in schema["required"])
    ):
        errors.append(f"{at}: required must be an array of property names")
    if "enum" in schema and (not isinstance(schema["enum"], list) or not schema["enum"]):
        errors.append(f"{at}: enum must be a non-empty array")
    if "pattern" in schema:
        try:
            re.compile(schema["pattern"])
        except (re.error, TypeError):
            errors.append(f"{at}: pattern must be a valid regular expression")
    properties = schema.get("properties", {})
    if not isinstance(properties, dict):
        errors.append(f"{at}: properties must be an object")
    else:
        for name, child in properties.items():
            errors.extend(check_schema(child, f"{at}.properties.{name}"))
    if "items" in schema:
        errors.extend(check_schema(schema["items"], f"{at}.items"))
    return errors


def _matches_type(value: object, expected: str) -> bool:
    return {
        "object": isinstance(value, dict),
        "array": isinstance(value, list),
        "string": isinstance(value, str),
        "boolean": type(value) is bool,
        "integer": type(value) is int,
        "number": type(value) in (int, float),
        "null": value is None,
    }[expected]


def validate_schema(value: object, schema: dict, at: str = "$", *, partial: bool = False) -> list[str]:
    """Validate a value against an already checked schema.

    Partial mode permits absent properties and unfinished arrays; present
    values must still have the declared types, enums and property names.
    """
    errors: list[str] = []
    expected = schema.get("type")
    if expected is not None and not _matches_type(value, expected):
        return [f"{at} must be {expected}, got {type(value).__name__}"]
    if partial and isinstance(value, str) and not value.strip():
        return []  # a blank form field is not an asserted value
    if "enum" in schema and not any(type(value) is type(choice) and value == choice for choice in schema["enum"]):
        errors.append(f"{at} must be one of {schema['enum']!r}, got {value!r}")
    if isinstance(value, str):
        if len(value) < schema.get("minLength", 0):
            errors.append(f"{at} must be non-empty (minLength {schema['minLength']})")
        if "pattern" in schema and re.search(schema["pattern"], value) is None:
            errors.append(f"{at} does not match pattern {schema['pattern']!r}")
    if isinstance(value, list):
        if not partial and len(value) < schema.get("minItems", 0):
            errors.append(f"{at} must contain at least {schema['minItems']} item(s)")
        if "items" in schema:
            for index, item in enumerate(value):
                errors.extend(validate_schema(item, schema["items"], f"{at}[{index}]", partial=partial))
    if isinstance(value, dict):
        properties = schema.get("properties", {})
        if not partial:
            for name in schema.get("required", []):
                if name not in value:
                    errors.append(f"{at}.{name} missing required field")
        for name, item in value.items():
            if name in properties:
                errors.extend(validate_schema(item, properties[name], f"{at}.{name}", partial=partial))
            elif schema.get("additionalProperties") is False:
                errors.append(f"{at} has unknown field: {name}")
    return errors
