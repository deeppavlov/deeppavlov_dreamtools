from pathlib import Path
from typing import Union

from deeppavlov_dreamtools import DreamDist


def local_yml(
    dist_name: str,
    dream_root: Union[Path, str],
    services: list,
    drop_ports: bool = True,
    single_replica: bool = True,
):
    dist = DreamDist.from_name(
        dist_name,
        dream_root,
        pipeline_conf=False,
        compose_override=False,
        compose_dev=True,
        compose_proxy=True,
        compose_local=False,
    )
    return dist.create_local_yml(services, drop_ports, single_replica)
