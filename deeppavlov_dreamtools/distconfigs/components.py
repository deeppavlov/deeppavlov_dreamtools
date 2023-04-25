import json
from pathlib import Path
from typing import Union, Type, Optional, List

from pydantic import parse_obj_as

from deeppavlov_dreamtools import utils
from deeppavlov_dreamtools.constants import (
    COMPONENT_CARD_FILENAME,
    COMPONENT_PIPELINE_FILENAME,
    COMPONENT_TEMPLATE_FILENAME,
)
from deeppavlov_dreamtools.distconfigs import generics, services
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


def create_agent_component(
    dream_root: Union[Path, str],
    agent_service: services.DreamService,
    config_path: Union[Path, str],
    name: str,
    display_name: str,
    author: str,
    description: str,
    group: str,
    response_text: str,
    tags: Optional[List[str]] = None,
):
    config_path = Path(config_path)
    source_dir = config_path.parent

    component = generics.Component(
        name=name,
        display_name=display_name,
        is_customizable=False,
        author=author,
        description=f"DP-Agent for {name}",
        group=group,
        connector=generics.PipelineConfConnector(
            protocol="python",
            class_name="PredefinedTextConnector",
            response_text=response_text,
            annotations={
                "sentseg": {
                    "punct_sent": response_text,
                    "segments": [f"{sentence.strip()}." for sentence in response_text.split(".") if sentence],
                }
            },
        ),
        service=agent_service.service_file,
        state_manager_method="add_bot_utterance_last_chance",
        tags=tags,
        endpoint="respond",
    )

    dream_component = DreamComponent(
        dream_root=dream_root,
        source_dir=source_dir,
        component_file=config_path,
        component=component,
        service=agent_service,
    )
    dream_component.save_configs()

    return dream_component


def create_generative_prompted_skill_component(
    dream_root: Union[Path, str],
    generative_prompted_skill_service: services.DreamService,
    config_path: Union[Path, str],
    name: str,
    display_name: str,
    author: str,
    description: str,
):
    config_path = Path(config_path)
    source_dir = config_path.parent

    component = generics.Component(
        name=name,
        display_name=display_name,
        is_customizable=True,
        author=author,
        description=description,
        ram_usage="150M",
        group="skills",
        connector=generics.PipelineConfConnector(protocol="http", timeout="5.0", url=""),
        dialog_formatter="state_formatters.dp_formatters:dff_empathetic_marketing_prompted_skill_formatter",
        response_formatter="state_formatters.dp_formatters:skill_with_attributes_formatter_service",
        previous_services=["skill_selectors"],
        state_manager_method="add_hypothesis",
        endpoint="respond",
        service=generative_prompted_skill_service.service_file,
    )

    dream_component = DreamComponent(
        dream_root=dream_root,
        source_dir=source_dir,
        component_file=config_path,
        component=component,
        service=generative_prompted_skill_service,
    )
    dream_component.save_configs()

    return dream_component


class DreamComponent:
    def __init__(
        self,
        dream_root: Union[Path, str],
        source_dir: Union[Path, str],
        component_file: Union[Path, str],
        component: generics.Component,
        service: services.DreamService,
        # template: DreamComponentTemplate = None,
    ):
        self.dream_root = dream_root
        self.source_dir = source_dir
        self.component_file = component_file
        self.component = component
        self.service = service
        # self.template = template

    # def _create_config_dir(self):
    #     config_dir = self.dream_root / self.source_dir
    #     config_dir.mkdir(parents=True, exist_ok=True)

    @classmethod
    def from_file(cls, path: Union[Path, str], dream_root: Union[Path, str] = None):
        path = Path(path)
        dream_root = Path(dream_root)

        source_dir = dream_root / path.parent
        component = generics.Component(**utils.load_yml(dream_root / path))

        service = services.DreamService.from_config_dir(dream_root, dream_root / component.service)

        return cls(dream_root, source_dir, path, component, service)

    def save_configs(self):
        self.source_dir.mkdir(parents=True, exist_ok=True)
        utils.dump_yml(utils.pydantic_to_dict(self.component), self.component_file)
        self.service.save_configs()

    @property
    def pipeline(self):
        return generics.PipelineConfService(
            is_enabled=True,
            source=generics.PipelineConfComponentSource(
                component=self.component_file,
                service=self.component.service,
            ),
            **self.component.dict(exclude_none=True),
        )


# def list_components()
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
