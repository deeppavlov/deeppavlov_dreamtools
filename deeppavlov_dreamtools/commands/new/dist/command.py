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
    dream_dist = DreamDist.from_template(
        name,
        dream_root,
        template_name,
        services,
        mk_pipeline_conf,
        mk_compose_override,
        mk_compose_dev,
        mk_compose_proxy,
        mk_compose_local,
    )
    paths = dream_dist.save(overwrite)

    return paths
