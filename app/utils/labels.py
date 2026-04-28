import json


def parse_custom_labels(raw_value: str | None) -> list[str]:
    # Returns an empty list on missing, empty, malformed, or non-list JSON.
    if not raw_value:
        return []
    try:
        decoded = json.loads(raw_value)
    except (ValueError, TypeError):
        return []
    if not isinstance(decoded, list):
        return []
    return [str(item) for item in decoded if str(item).strip()]
