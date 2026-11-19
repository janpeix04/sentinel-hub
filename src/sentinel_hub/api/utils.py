from typing import Any


def remove_undefined(payload: dict) -> dict:
    """Takes a dictionary and removes keys without value."""
    return {name: value for name, value in payload.items() if value is not None}


def _update_other_args(dict1: dict[str, Any], dict2: dict[str, Any]) -> None:
    """Function for a recursive update of `dict1` with `dict2`. The function loops over the keys in `dict2` and
    only the non-dict like values are assigned to the specified keys.
    """
    for key, value in dict2.items():
        if isinstance(value, dict) and key in dict1:
            _update_other_args(dict1[key], value)
        else:
            dict1[key] = value
