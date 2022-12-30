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
from datetime import datetime
from pathlib import Path
import re
from typing import Dict, Union, Optional, Any, List, Type

from pydantic import BaseModel, Extra, validator

from deeppavlov_dreamtools.utils import parse_connector_url


def convert_datetime_to_str(dt: datetime) -> str:
    """Converts datetime object into ISO 8601 string without ms

    Args:
        dt: datetime object

    Returns:
        ISO 8601 datetime string
    """

    return dt.strftime('%Y-%m-%dT%H:%M:%S')


class BaseModelNoExtra(BaseModel):
    """
    Implements BaseModel which throws an Exception when children are instantiated with extra kwargs
    """

    class Config:
        extra = Extra.forbid
        json_encoders = {
            # custom output conversion for datetime
            datetime: convert_datetime_to_str
        }


class PipelineConfConnector(BaseModelNoExtra):
    protocol: str
    timeout: Optional[float]
    url: Optional[str]
    class_name: Optional[str]
    response_text: Optional[str]
    annotations: Optional[Dict[str, Any]]
    annotator_names: Optional[list]


class PipelineConfService(BaseModelNoExtra):
    is_enabled: Optional[bool] = True
    connector: Union[str, PipelineConfConnector]
    dialog_formatter: Optional[str]
    response_formatter: Optional[str]
    previous_services: Optional[List[str]]
    required_previous_services: Optional[List[str]]
    state_manager_method: Optional[str]
    tags: Optional[List[str]]

    @property
    def container_name(self):
        try:
            url = self.connector.url
        except AttributeError:
            name = None
        else:
            host, port, endpoint = parse_connector_url(url)
            name = host

        return name

    @property
    def container_port(self):
        try:
            url = self.connector.url
        except AttributeError:
            port = None
        else:
            host, port, endpoint = parse_connector_url(url)

        return port


class PipelineConfServiceList(BaseModelNoExtra):
    last_chance_service: Optional[PipelineConfService]
    timeout_service: Optional[PipelineConfService]
    annotators: Dict[str, PipelineConfService]
    response_annotators: Optional[Dict[str, PipelineConfService]]
    response_annotator_selectors: Optional[PipelineConfService]
    candidate_annotators: Optional[Dict[str, PipelineConfService]]
    skill_selectors: Optional[Dict[str, PipelineConfService]]
    skills: Dict[str, PipelineConfService]
    response_selectors: Dict[str, PipelineConfService]

    @property
    def editable_groups(self):
        group_names = [
            "annotators",
            "response_annotators",
            "candidate_annotators",
            "skills",
            "response_selectors",
        ]

        groups = []
        for name in group_names:
            if getattr(self, name):
                groups.append(name)

        return groups


class PipelineConfMetadata(BaseModelNoExtra):
    display_name: str
    author: str
    description: str
    version: str
    date_created: datetime
    ram_usage: str
    gpu_usage: str
    disk_usage: str


class PipelineConf(BaseModelNoExtra):
    """
    Implements pipeline.json config structure
    """

    connectors: Optional[Dict[str, PipelineConfConnector]]
    services: PipelineConfServiceList
    metadata: Optional[PipelineConfMetadata]


class ContainerBuildDefinition(BaseModelNoExtra):
    args: Optional[Dict[str, Any]]
    context: Path
    dockerfile: Optional[Path]

    class Config:
        json_encoders = {Path: str}


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
        return v


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
    ports: Optional[List[str]]

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
                    {
                        "key": f"environment -> {env_name}",
                        "text": env_value,
                        "value": env_value,
                    }
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


class ComponentMetadata(BaseModelNoExtra):
    type: str
    display_name: str
    author: str
    description: str
    version: str
    date_created: datetime
    ram_usage: str
    gpu_usage: str
    disk_usage: str
    execution_time: float


class Component(BaseModelNoExtra):
    name: str
    group: str
    assistant_dist: str
    port: Optional[int]
    pipeline_conf: Optional[PipelineConfService]
    compose_override: Optional[ComposeContainer]
    compose_dev: Optional[ComposeDevContainer]
    compose_proxy: Optional[ComposeContainer]
    compose_local: Optional[ComposeLocalContainer]
    metadata: Optional[ComponentMetadata]


AnyContainer = Union[ComposeContainer, ComposeDevContainer, ComposeLocalContainer]
AnyComposeConfig = Union[ComposeOverride, ComposeDev, ComposeProxy, ComposeLocal]
AnyConfig = Union[PipelineConf, ComposeOverride, ComposeDev, ComposeProxy, ComposeLocal]
AnyConfigType = Type[Union[PipelineConf, ComposeOverride, ComposeDev, ComposeProxy, ComposeLocal]]
