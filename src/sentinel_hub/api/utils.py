def remove_undefined(payload: dict) -> dict:
    """Takes a dictionary and removes keys without value."""
    return {name: value for name, value in payload.items() if value is not None}
