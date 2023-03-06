from pathlib import Path
from typing import Union, Type, Optional

from pydantic import parse_obj_as

from deeppavlov_dreamtools import utils
from deeppavlov_dreamtools.constants import COMPONENT_CARD_FILENAME, COMPONENT_PIPELINE_FILENAME
from deeppavlov_dreamtools.distconfigs.generics import Component, PipelineConfServiceComponent
from deeppavlov_dreamtools.utils import parse_connector_url


class DreamComponent:
    def __init__(
        self,
        component_dir: Union[Path, str],
        config: Component,
        pipeline: PipelineConfServiceComponent,
        container_name: str,
        group: str,
        endpoint: Optional[str] = None,
    ):
        self.component_dir = Path(component_dir)
        self.config = config
        self.pipeline = pipeline
        self.container_name = container_name
        self.group = group
        self.endpoint = endpoint

    @classmethod
    def from_component_dir(
        cls, path: Union[str, Path], container_name: str, group: str, endpoint: Optional[str] = None
    ):
        """
        Loads component from directory path.

        Directory must contain component.yml and pipeline.yml config files

        Args:
            path: path to component directory
            container_name: name of the specific container config
            group: group name, e.g. annotators, skills, etc.
            endpoint: endpoint name

        Returns:
            DreamComponent config instance
        """
        path = Path(path)
        config_path = path / COMPONENT_CARD_FILENAME
        pipeline_path = path / COMPONENT_PIPELINE_FILENAME

        try:
            config = utils.load_yml(config_path)
            pipeline = utils.load_yml(pipeline_path)
        except FileNotFoundError:
            raise FileNotFoundError(f"{container_name} {group} {endpoint} does not exist in {path}")

        try:
            config = parse_obj_as(Component, config[container_name])
        except KeyError:
            raise KeyError(f"{container_name} container does not exist in {config_path}")

        pipeline_dict = None
        try:
            for pl in pipeline[container_name]:

                if pl["group"] == group:

                    if endpoint:
                        if pl["connector"].get("url"):
                            _, _, pl_endpoint = parse_connector_url(pl["connector"]["url"])
                            if endpoint == pl_endpoint:
                                pipeline_dict = pl
                        else:
                            raise ValueError(f"Endpoint {endpoint} not defined for {group} in {pipeline_path}")
                    else:
                        pipeline_dict = pl

                if pipeline_dict:
                    pipeline = parse_obj_as(PipelineConfServiceComponent, pipeline_dict)

        except KeyError:
            raise KeyError(f"{container_name} container does not exist in {pipeline_path}")

        return cls(path, config, pipeline, container_name, group, endpoint)
