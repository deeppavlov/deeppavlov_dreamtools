import json
from pathlib import Path
from typing import Union, Type, Optional, List

from pydantic import parse_obj_as

from deeppavlov_dreamtools import utils
from deeppavlov_dreamtools.constants import COMPONENT_CARD_FILENAME, COMPONENT_PIPELINE_FILENAME
from deeppavlov_dreamtools.distconfigs.generics import Component, PipelineConfServiceComponent
from deeppavlov_dreamtools.utils import parse_connector_url


class ComponentRepository:
    def __init__(self, dream_root: Union[Path, str]):
        self.dream_root = Path(dream_root)

    def add_component_config(self, group: str, name: str, config: Component):
        component_card_path = self.dream_root / group / name / "component.yml"
        component_card = utils.load_yml(component_card_path)
        component_card[config.container_name] = json.loads(config.json(exclude_none=True))
        utils.dump_yml(component_card, component_card_path, overwrite=True)

    def add_generative_prompted_skill(
        self,
        name: str,
        display_name: str,
        container_name: str,
        author: str,
        description: str,
        ram_usage: str,
        port: int,
        lm_service: str,
        gpu_usage: Optional[str] = None,
    ):
        component = Component(
            name=name,
            display_name=display_name,
            container_name=container_name,
            component_type="Generative",
            model_type="NN-based",
            is_customizable=True,
            author=author,
            description=description,
            ram_usage=ram_usage,
            gpu_usage=gpu_usage,
            port=port,
            endpoints=[
                {
                    "group": "skills",
                    "endpoint": "respond"
                }
            ],
            build_args={
                "SERVICE_PORT": port,
                "SERVICE_NAME": name,
                "PROMPT_FILE": f"common/prompts/{name}.json",
                "GENERATIVE_SERVICE_URL": f"http://{lm_service}:8130/respond",
                "GENERATIVE_SERVICE_CONFIG": "default_generative_config.json",
                "GENERATIVE_TIMEOUT": 5,
                "N_UTTERANCES_CONTEXT": 3
            },
            compose_override={
                "env_file": [
                    ".env"
                ],
                "build": {
                    "args": {
                        "SERVICE_PORT": port,
                        "SERVICE_NAME": name,
                        "PROMPT_FILE": f"common/prompts/{name}.json",
                        "GENERATIVE_SERVICE_URL": f"http://{lm_service}:8130/respond",
                        "GENERATIVE_SERVICE_CONFIG": "default_generative_config.json",
                        "GENERATIVE_TIMEOUT": 5,
                        "N_UTTERANCES_CONTEXT": 3
                    },
                    "context": ".",
                    "dockerfile": "./skills/dff_template_prompted_skill/Dockerfile"
                },
                "command": f"gunicorn --workers=1 server:app -b 0.0.0.0:{port} --reload",
                "deploy": {
                    "resources": {
                        "limits": {
                            "memory": "128M"
                        },
                        "reservations": {
                            "memory": "128M"
                        }
                    }
                }
            },
            compose_dev={
                "volumes": [
                    "./skills/dff_template_prompted_skill:/src",
                    "./common:/src/common"
                ],
                "ports": [
                    f"{port}:{port}"
                ]
            },
            compose_proxy={}
        )
        self.add_component_config("skills", "dff_template_prompted_skill", component)


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
