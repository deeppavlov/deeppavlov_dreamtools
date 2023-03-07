from pathlib import Path
from typing import Union

from deeppavlov_dreamtools import AssistantDist


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
    """Creates new dff skill from template.
    Throws an exception if the directory exists.

    Args:
        name: DFF skill name
        dream_root: Dream root directory
        dream_dist: Dream distribution name
        port: port where new DFF skill should be deployed
        compose_override: add definition to docker-compose.override.yml
        compose_dev: add definition to dev.yml
        compose_proxy: add definition to proxy.yml
        compose_local: add definition to local.yml

    Returns:
        path to created DFF skill.

    """
    dist = AssistantDist.from_name(
        dream_dist,
        dream_root,
        pipeline_conf=True,
        compose_override=compose_override,
        compose_dev=compose_dev,
        compose_proxy=compose_proxy,
        compose_local=compose_local,
    )
    return dist.add_dff_skill(name, port)
