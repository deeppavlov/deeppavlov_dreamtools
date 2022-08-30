from pathlib import Path
from typing import Union

from deeppavlov_dreamtools import DreamDist


def dist(
    name: str,
    dream_root: Union[Path, str],
    template_name: str,
    services: list = None,
    overwrite: bool = False,
    mk_pipeline_conf: bool = False,
    mk_compose_override: bool = False,
    mk_compose_dev: bool = False,
    mk_compose_proxy: bool = False,
    mk_compose_local: bool = False,
):
    """Creates new Dream distribution from template.
    Throws an exception if the directory exists and overwrite=False.

    Args:
        name: new Dream distribution name
        dream_root:
        template_name:
        services:
        overwrite:
        mk_pipeline_conf:
        mk_compose_override:
        mk_compose_dev:
        mk_compose_proxy:
        mk_compose_local:

    Returns:

    """
    dream_dist = DreamDist.from_name(
        template_name,
        dream_root,
        mk_pipeline_conf,
        mk_compose_override,
        mk_compose_dev,
        mk_compose_proxy,
        mk_compose_local,
    )
    new_dist = dream_dist.create_dist(
        name,
        dream_root,
        services,
        mk_pipeline_conf,
        mk_compose_override,
        mk_compose_dev,
        mk_compose_proxy,
        mk_compose_local,
    )
    paths = new_dist.save(overwrite)

    return paths
