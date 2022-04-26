import logging


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
