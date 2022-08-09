"""
Required:
pipeline_conf.json - dream pipeline
docker-compose.yml - agent, mongo
docker-compose.override.yml - agent (cmd, wait_hosts), main container definitions

Optional:
dev.yml - volumes and ports
local.yml - nginx tunnels currently in use
proxy.yml - all nginx tunnels

"""
import re
from pathlib import Path
from typing import Dict, Union, Optional, Any, List, Tuple, Literal, Type

from pydantic import BaseModel, Extra, validator


class BaseModelNoExtra(BaseModel, extra=Extra.forbid):
    """
    Implements BaseModel which throws an Exception when children are instantiated with extra kwargs
    """


class PipelineConfConnector(BaseModelNoExtra):
    # name: str
    protocol: str
    timeout: Optional[float]
    url: Optional[str]
    _host: Optional[str]
    _port: Optional[str]
    _endpoint: Optional[str]
    class_name: Optional[str]
    response_text: Optional[str]
    annotations: Optional[Dict[str, Any]]
    annotator_names: Optional[list]


class PipelineConfService(BaseModelNoExtra):
    connector: Union[str, PipelineConfConnector]
    dialog_formatter: Optional[str]
    response_formatter: Optional[str]
    previous_services: Optional[List[str]]
    required_previous_services: Optional[List[str]]
    state_manager_method: Optional[str]
    tags: Optional[List[str]]

    @property
    def connector_url(self):
        try:
            url = self.connector.url
        except AttributeError:
            url = None
        return url


class PipelineConfServiceList(BaseModelNoExtra):
    last_chance_service: PipelineConfService
    timeout_service: PipelineConfService
    bot_annotator_selector: PipelineConfService
    post_annotators: Dict[str, PipelineConfService]
    annotators: Dict[str, PipelineConfService]
    skill_selectors: Dict[str, PipelineConfService]
    skills: Dict[str, PipelineConfService]
    post_skill_selector_annotators: Dict[str, PipelineConfService]
    response_selectors: Dict[str, PipelineConfService]

    @property
    def flat_keys(self):
        return ["last_chance_service", "timeout_service", "bot_annotator_selector"]

    @property
    def editable_groups(self):
        return [
            "post_annotators",
            "annotators",
            # "skill_selectors",
            "skills",
            "post_skill_selector_annotators",
            "response_selectors",
        ]

    # @property
    # def flattened_dict(self) -> Dict[str, PipelineConfService]:
    #     flattened_service_dict = {
    #         **self.post_annotators,
    #         **self.annotators,
    #         **self.skill_selectors,
    #         **self.skills,
    #         **self.post_skill_selector_annotators,
    #         **self.response_selectors,
    #         "last_chance_service": self.last_chance_service,
    #         "timeout_service": self.timeout_service,
    #         "bot_annotator_selector": self.bot_annotator_selector,
    #     }
    #
    #     return flattened_service_dict


class PipelineConf(BaseModelNoExtra):
    """
    Implements pipeline.json config structure
    """
    connectors: Dict[str, PipelineConfConnector]
    services: PipelineConfServiceList


class ContainerBuildDefinition(BaseModelNoExtra):
    args: Optional[Dict[str, Any]]
    context: Path
    dockerfile: Optional[Path]

    class Config:
        json_encoders = {
            Path: str
        }


class DeploymentDefinitionResourcesArg(BaseModelNoExtra):
    memory: str

    @validator("memory")
    def check_memory_format(cls, v):
        memory_unit = v[-1]
        memory_value = v[:-1]

        if memory_unit not in ["G", "M"]:
            raise ValueError("'memory' value must contain units, e.g. '2.5G' or '256M'")
        try:
            float(memory_value)
        except ValueError:
            raise ValueError(
                "'memory' value must contain a float-like value before the unit substring, e.g. '2.5G' or '256M'"
            )


class DeploymentDefinitionResources(BaseModelNoExtra):
    limits: DeploymentDefinitionResourcesArg
    reservations: DeploymentDefinitionResourcesArg


class DeploymentDefinition(BaseModelNoExtra):
    mode: Optional[str]
    replicas: Optional[int]
    resources: Optional[DeploymentDefinitionResources]


class ComposeContainer(BaseModelNoExtra):
    volumes: Optional[List[str]]
    env_file: Optional[list]
    build: Optional[ContainerBuildDefinition]
    command: Optional[Union[list, str]]
    environment: Optional[Union[Dict[str, Any], list]]
    deploy: Optional[DeploymentDefinition]
    tty: Optional[bool]

    @property
    def port_definitions(self):
        ports = []

        # command
        try:
            port = re.findall(
                r"-p (\d{3,6})|--port (\d{3,6})|\d+?.\d+?.\d+?.\d+?:(\d{3,6})",
                self.command,
            )[0]
            ports.append(
                {
                    "key": "command",
                    "text": self.command,
                    "value": port[0] or port[1] or port[2],
                }
            )
        except IndexError:
            pass

        try:
            value = self.build.args["SERVICE_PORT"]
            key = "build -> args -> SERVICE_PORT"
            ports.append({"key": key, "text": value, "value": value})
        except KeyError:
            pass

        # environment
        iterator = []

        if isinstance(self.environment, list):
            iterator = [e.split("=") for e in self.environment]
        elif isinstance(self.environment, dict):
            iterator = self.environment.items()

        for env_name, env_value in iterator:
            if env_name == "PORT":
                ports.append(
                    {"key": f"environment -> {env_name}", "text": env_value, "value": env_value}
                )

        return ports


class ComposeDevContainer(BaseModelNoExtra):
    volumes: Optional[List[str]]
    ports: List[str]


class ComposeLocalContainer(ComposeContainer, ComposeDevContainer):
    ports: Optional[List[str]]


class BaseComposeConfigModel(BaseModelNoExtra):
    """
    Implements basic .yml config structure.
    Particular .yml configs should inherit from this one instead of BaseModel.
    """
    services: Dict
    version: str = "3.7"


class ComposeOverride(BaseComposeConfigModel):
    """
    Implements docker-compose.override.yml config structure
    """
    services: Dict[str, ComposeContainer]


class ComposeDev(BaseComposeConfigModel):
    """
    Implements dev.yml config structure
    """
    services: Dict[str, ComposeDevContainer]


class ComposeProxy(BaseComposeConfigModel):
    """
    Implements proxy.yml config structure
    """
    services: Dict[str, ComposeContainer]


class ComposeLocal(BaseComposeConfigModel):
    """
    Implements proxy.yml config structure
    """
    services: Dict[str, ComposeLocalContainer]


AnyContainer = Union[ComposeContainer, ComposeDevContainer, ComposeLocalContainer]
AnyConfig = Union[PipelineConf, ComposeOverride, ComposeDev, ComposeProxy, ComposeLocal]
AnyConfigType = Type[Union[PipelineConf, ComposeOverride, ComposeDev, ComposeProxy, ComposeLocal]]
