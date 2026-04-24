from typing import Any


def _plain_text(items: list[dict]) -> str:
    return "".join(item.get("plain_text", "") for item in items)


def flatten_property(prop: dict) -> Any:
    kind = prop.get("type")
    value = prop.get(kind) if kind else None

    if value is None:
        return None

    if kind in ("title", "rich_text"):
        return _plain_text(value)
    if kind in ("number", "checkbox", "url", "email", "phone_number"):
        return value
    if kind == "select":
        return value.get("name")
    if kind == "status":
        return value.get("name")
    if kind == "multi_select":
        return [item.get("name") for item in value]
    if kind == "date":
        return {"start": value.get("start"), "end": value.get("end")}
    if kind == "people":
        return [p.get("name") or p.get("id") for p in value]
    if kind == "relation":
        return [r.get("id") for r in value]
    if kind == "files":
        return [f.get("name") for f in value]
    if kind == "formula":
        inner = value.get("type")
        return value.get(inner) if inner else None
    if kind == "rollup":
        inner = value.get("type")
        if inner == "array":
            return [flatten_property(item) for item in value.get("array", [])]
        return value.get(inner) if inner else None
    if kind == "unique_id":
        prefix = value.get("prefix")
        number = value.get("number")
        return f"{prefix}-{number}" if prefix else number
    if kind == "created_time":
        return value
    if kind == "last_edited_time":
        return value
    if kind == "created_by" or kind == "last_edited_by":
        return value.get("name") or value.get("id")

    return value


def flatten_page(page: dict) -> dict:
    flat: dict[str, Any] = {"id": page.get("id")}
    for name, prop in page.get("properties", {}).items():
        flat[name] = flatten_property(prop)
    return flat
