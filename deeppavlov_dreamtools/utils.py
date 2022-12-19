import logging
from typing import Optional, Tuple


def create_logger(
    name: str,
    fmt: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level: str = "INFO",
) -> logging.Logger:
    logger = logging.getLogger(name)
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter(fmt))
    logger.addHandler(handler)
    logger.setLevel(level)

    return logger


def parse_connector_url(url: str) -> Tuple[str, str, str]:
    """
    Deserializes a string into host, port, endpoint components.

    Args:
        url: Full url string of format http(s)://{host}:{port}/{endpoint}.
            If empty, returns (None, None, None)

    Returns:
        tuple of (host, port, endpoint)

    Raises:
        ValueError if not appropriate url string format
    """
    try:
        url_without_protocol = url.split("//")[-1]
        url_parts = url_without_protocol.split("/", maxsplit=1)

        host, port = url_parts[0].split(":")
    except (AttributeError, ValueError):
        raise ValueError(f"{url} does not fit the http(s)://{{host}}:{{port}}/{{endpoint}} format")

    endpoint = ""
    if len(url_parts) > 1:
        endpoint = url_parts[1]

    return host, port, endpoint


def iter_field_keys_values(search_dict: dict, field: str):
    """
    Takes a dict with nested lists and dicts,
    and searches all dicts for a key of the field
    provided.
    """
    for key, value in search_dict.items():

        if key == field:
            yield key, value

        elif isinstance(value, dict):
            yield from iter_field_keys_values(value, field)

        elif isinstance(value, list):
            for item in value:
                if isinstance(item, dict):
                    yield from iter_field_keys_values(item, field)
