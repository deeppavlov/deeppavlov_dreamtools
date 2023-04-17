import json
from pathlib import Path
from typing import Union, Type, Optional, List

from pydantic import parse_obj_as

from deeppavlov_dreamtools import utils
from deeppavlov_dreamtools.constants import COMPONENT_CARD_FILENAME, COMPONENT_PIPELINE_FILENAME, COMPONENT_TEMPLATE_FILENAME
from deeppavlov_dreamtools.distconfigs import generics
from deeppavlov_dreamtools.utils import parse_connector_url


class MissingPipelineException(Exception):
    """"""


class DreamComponentTemplate:
    def __init__(self, config: generics.ComponentTemplate, file_path: str, name: str):
        self.config = config
        self.file_path = file_path
        self.name = name

    @classmethod
    def from_file(cls, file_path: Union[Path, str], name: str):
        """
        Loads template with the given name from template file

        Args:
            file_path: path to template file
            name: template name

        Returns:
            DreamComponentTemplate instance

        Raises:
            ValueError: template with the given name does not exist in the file
        """
        template_card = utils.load_yml(file_path)
        template_config = None

        for template in template_card:
            if template["name"] == name:
                template_config = template
                break

        if not template_config:
            raise ValueError(f"Template {name} not found in {file_path}")

        return cls(config=generics.ComponentTemplate(**template_config), file_path=file_path, name=name)

    def save(self) -> None:
        utils.dump_yml(self.config, self.file_path, overwrite=True)


class DreamComponent:
    def __init__(
        self,
        component_dir: Union[Path, str],
        config: generics.Component,
        pipeline: generics.PipelineConfServiceComponent,
        container_name: str,
        group: str,
        template: DreamComponentTemplate = None,
        endpoint: str = None,
    ):
        self.component_dir = Path(component_dir)
        self.config = config
        self.pipeline = pipeline
        self.container_name = container_name
        self.group = group
        self.template = template
        self.endpoint = endpoint

    @classmethod
    def from_component_dir(
        cls,
        path: Union[str, Path],
        container_name: str,
        group: str,
        template_name: str = None,
        endpoint: Optional[str] = None,
    ):
        """
        Loads component from directory path.

        Directory must contain component.yml and pipeline.yml config files

        Args:
            path: path to component directory
            container_name: name of the specific container config
            group: group name, e.g. annotators, skills, etc.
            template_name: name of the specific template
            endpoint: endpoint name

        Returns:
            DreamComponent config instance
        """
        path = Path(path)
        config_path = path / COMPONENT_CARD_FILENAME
        pipeline_path = path / COMPONENT_PIPELINE_FILENAME

        config_card = utils.load_yml(config_path)
        try:
            pipeline_card = utils.load_yml(pipeline_path)
        except FileNotFoundError:
            pipeline_card = None
            # SILENCED FOR NOW
            # raise FileNotFoundError(f"{container_name} {group} {endpoint} does not exist in {path}")

        try:
            config_dict = config_card[container_name]
        except KeyError:
            raise KeyError(f"{container_name} container does not exist in {config_path}")

        try:
            template_name = config_dict["template"]
            template = DreamComponentTemplate.from_file(path / COMPONENT_TEMPLATE_FILENAME, template_name)
            template_config = template.config
            del config_dict["template"]
        except KeyError:
            template = template_config = None

        config = generics.Component(
            template=template_config,
            **config_dict,
        )

        pipeline_dict = None
        try:
            for pl in pipeline_card[container_name]:
                if pl["group"] == group:
                    if endpoint:
                        if pl["endpoint"]:
                            if endpoint == pl["endpoint"]:
                                pipeline_dict = pl
                                break
                        else:
                            raise ValueError(f"Endpoint {endpoint} not defined for {group} in {pipeline_path}")
                    else:
                        pipeline_dict = pl
                        break

            if not pipeline_dict:
                raise ValueError(f"Endpoint {endpoint} not defined for {group} in {pipeline_path} (container {container_name})")

            pipeline = generics.PipelineConfServiceComponent(**pipeline_dict)

        except KeyError:
            # raise MissingPipelineException(f"{container_name} container does not exist in {pipeline_path}")
            pipeline = None
        except TypeError:
            # if endpoint is None:
            #     pipeline = None
            # else:
            #     raise MissingPipelineException(f"{pipeline_path} does not contain a valid pipeline.yml")
            pipeline = None
        except ValueError:
            # if group == "services":
            #     pipeline = None
            # else:
            #     raise
            pipeline = None

        return cls(
            path,
            config,
            pipeline,
            container_name,
            group,
            template,
            endpoint,
        )


class ComponentRepository:
    def __init__(self, dream_root: Union[Path, str]):
        self.dream_root = Path(dream_root)
        self.components = None

    def _iter_components(self):
        for component_card_path in self.dream_root.rglob(COMPONENT_CARD_FILENAME):
            component_card = utils.load_yml(component_card_path)

            for name, component in component_card.items():
                for endpoint in component["endpoints"]:
                    yield DreamComponent.from_component_dir(
                        component_card_path.parent,
                        component["container_name"],
                        endpoint["group"],
                        component.get("template"),
                        endpoint=endpoint["endpoint"],
                    )

    def scan_components(self):
        self.components = list(self._iter_components())
        return self.components

    def add_component_config(self, group: str, name: str, config: generics.Component):
        component_card_path = self.dream_root / group / name / "component.yml"
        component_card = utils.load_yml(component_card_path)
        component_card[config.container_name] = json.loads(config.json(exclude_none=True))
        utils.dump_yml(component_card, component_card_path, overwrite=True)

        return config

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
        prompt: str,
        gpu_usage: Optional[str] = None,
    ):
        prompt_file = f"common/prompts/{name}.json"

        component = generics.Component(
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
            endpoints=[{"group": "skills", "endpoint": "respond"}],
            build_args={
                "SERVICE_PORT": port,
                "SERVICE_NAME": name,
                "PROMPT_FILE": f"common/prompts/{name}.json",
                "GENERATIVE_SERVICE_URL": f"http://{lm_service}:8130/respond",
                "GENERATIVE_SERVICE_CONFIG": "default_generative_config.json",
                "GENERATIVE_TIMEOUT": 5,
                "N_UTTERANCES_CONTEXT": 3,
            },
            compose_override={
                "env_file": [".env"],
                "build": {
                    "args": {
                        "SERVICE_PORT": port,
                        "SERVICE_NAME": name,
                        "PROMPT_FILE": prompt_file,
                        "GENERATIVE_SERVICE_URL": f"http://{lm_service}:8130/respond",
                        "GENERATIVE_SERVICE_CONFIG": "default_generative_config.json",
                        "GENERATIVE_TIMEOUT": 5,
                        "N_UTTERANCES_CONTEXT": 3,
                    },
                    "context": ".",
                    "dockerfile": "./skills/dff_template_prompted_skill/Dockerfile",
                },
                "command": f"gunicorn --workers=1 server:app -b 0.0.0.0:{port} --reload",
                "deploy": {"resources": {"limits": {"memory": "128M"}, "reservations": {"memory": "128M"}}},
            },
            compose_dev={
                "volumes": ["./skills/dff_template_prompted_skill:/src", "./common:/src/common"],
                "ports": [f"{port}:{port}"],
            },
            compose_proxy={},
        )
        utils.dump_json({"prompt": prompt}, self.dream_root / prompt_file)
        return self.add_component_config("skills", "dff_template_prompted_skill", component)
