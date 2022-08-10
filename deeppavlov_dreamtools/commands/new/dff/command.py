from pathlib import Path
from typing import Union

from deeppavlov_dreamtools import DreamDist


def dff(
    name: str,
    dream_root: Union[str, Path],
    dream_dist: str,
    port: int,
    compose_override: bool,
    compose_dev: bool,
    compose_proxy: bool,
    compose_local: bool,
) -> Path:
    """Create new dff skill from template.
    Throws an exception if the directory exists.

    :param name: dff skill name
    :param dream_root: Dream root directory
    :param dream_dist: Dream distribution name
    :return: path to created dff skill.
    """
    dist = DreamDist.from_name(
        dream_dist,
        dream_root,
        True,
        compose_override,
        compose_dev,
        compose_proxy,
        compose_local,
    )
    return dist.add_dff_skill(name, port)
