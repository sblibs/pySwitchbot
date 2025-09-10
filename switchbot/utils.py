"""Utility functions for switchbot."""

from functools import lru_cache


@lru_cache(maxsize=512)
def format_mac_upper(mac: str) -> str:
    """Format the mac address string to uppercase with colons."""
    to_test = mac

    if len(to_test) == 17 and to_test.count(":") == 5:
        return to_test.upper()

    if len(to_test) == 17 and to_test.count("-") == 5:
        to_test = to_test.replace("-", "")
    elif len(to_test) == 14 and to_test.count(".") == 2:
        to_test = to_test.replace(".", "")

    if len(to_test) == 12:
        # no : included
        return ":".join(to_test.upper()[i : i + 2] for i in range(0, 12, 2))

    # Not sure how formatted, return original
    return mac.upper()
