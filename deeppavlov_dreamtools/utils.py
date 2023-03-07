import json
import logging
from pathlib import Path
from typing import Tuple, Union, Any

import yaml

from deeppavlov_dreamtools.distconfigs import const


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


def load_json(path: Union[Path, str]):
    with open(path, "r", encoding="utf-8") as json_f:
        data = json.load(json_f)

    return data


def dump_json(data: Any, path: Union[Path, str], overwrite: bool = False):
    mode = "w" if overwrite else "x"
    with open(path, mode, encoding="utf-8") as yml_f:
        json.dump(data, yml_f, indent=4)

    return path


def load_yml(path: Union[Path, str]):
    with open(path, "r", encoding="utf-8") as yml_f:
        data = yaml.load(yml_f, yaml.FullLoader)

    return data


def dump_yml(data: Any, path: Union[Path, str], overwrite: bool = False):
    mode = "w" if overwrite else "x"
    with open(path, mode, encoding="utf-8") as yml_f:
        yaml.dump(data, yml_f, sort_keys=False)

    return path


def resolve_all_paths(
    dist_path: Union[str, Path] = None,
    name: str = None,
    dream_root: Union[str, Path] = None,
):
    """
    Resolves path to Dream distribution, its name, and Dream root path
    from either ``dist_path`` or ``name`` and ``dream_root``.

    Args:
        dist_path: path to Dream distribution
        name: name of Dream distribution
        dream_root: path to Dream root directory

    Returns:
        tuple of (distribution path, distribution name, dream root path)

    Raises:
        ValueError: not enough arguments to resolve
        NotADirectoryError: dist_path is not a valid Dream distribution directory
    """
    if dist_path:
        name, dream_root = resolve_name_and_dream_root(dist_path)
    elif name and dream_root:
        dist_path = resolve_dist_path(name, dream_root)
    else:
        raise ValueError("Provide either dist_path or name and dream_root")

    dist_path = Path(dist_path)
    if not dist_path.exists() and dist_path.is_dir():
        raise NotADirectoryError(f"{dist_path} is not a Dream distribution")

    return dist_path, name, dream_root


def resolve_dist_path(name: str, dream_root: Union[str, Path]):
    """
    Resolves path to Dream distribution from name and Dream root path.

    Args:
        name: name of Dream distribution
        dream_root: path to Dream root directory

    Returns:
        path to Dream distribution

    """
    return Path(dream_root) / const.ASSISTANT_DISTS_DIR_NAME / name


def resolve_name_and_dream_root(path: Union[str, Path]):
    """
    Resolves name and Dream root directory path from Dream distribution path.

    Args:
        path: path to Dream distribution

    Returns:
        tuple of (name of Dream distribution, path to Dream root directory)

    """
    path = Path(path)
    return path.name, path.parents[1]


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
