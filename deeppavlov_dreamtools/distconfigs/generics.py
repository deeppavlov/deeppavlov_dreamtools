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
from typing import Dict, Union, Optional, Any, List, Type, Literal

from pydantic import field_validator, ConfigDict, BaseModel, Field, EmailStr

from deeppavlov_dreamtools.utils import parse_connector_url


def check_memory_format(value: Optional[str]) -> None:
    """Checks if the string has the correct memory format

    Args:
        value: string containing memory usage

    Raises:
        Value error if value is not in the correct format
    """
    if value is not None:
        try:
            memory_unit = value[-1]
            memory_value = value[:-1]
        except IndexError:
            raise ValueError("'memory' value must contain a float-like value and units, e.g. '2.5G' or '256M'")

        if memory_unit not in ["G", "M"]:
            raise ValueError("'memory' value must contain units, e.g. '2.5G' or '256M'")
        try:
            float(memory_value)
        except ValueError:
            raise ValueError(
                "'memory' value must contain a float-like value before the unit substring, e.g. '2.5G' or '256M'"
            )


def convert_datetime_to_str(dt: datetime) -> str:
    """Converts datetime object into ISO 8601 string without ms

    Args:
        dt: datetime object

    Returns:
        ISO 8601 datetime string
    """

    return dt.strftime("%Y-%m-%dT%H:%M:%S")


def _default_datetime():
    return datetime.utcnow().replace(microsecond=0)


class DateCreatedFieldMixin(BaseModel):
    date_created: datetime = Field(default_factory=_default_datetime)


class BaseModelNoExtra(BaseModel):
    """
    Implements BaseModel which throws an Exception when children are instantiated with extra kwargs
    """
    model_config = ConfigDict(extra="forbid")


COMPONENT_TYPES = Literal[
    "Script-based with NNs",
    "Script-based w/o NNs",
    "Fallback",
    "Generative",
    "FAQ",
    "Retrieval",
]

MODEL_TYPES = Literal[
    "Dictionary/Pattern-based",
    "NN-based",
    "ML-based",
    "External API",
]


class PipelineConfConnector(BaseModelNoExtra):
    protocol: str
    timeout: Optional[float] = None
    url: Optional[str] = None
    class_name: Optional[str] = None
    response_text: Optional[str] = None
    annotations: Optional[Dict[str, Any]] = None
    annotator_names: Optional[list] = None


class PipelineConfComponentSource(BaseModelNoExtra):
    component: Path
    service: Path


class PipelineConfServiceComponent(BaseModel):
    group: Optional[str] = None
    connector: Union[str, PipelineConfConnector]
    dialog_formatter: Optional[Union[str, dict]] = None
    response_formatter: Optional[str] = None
    previous_services: Optional[List[str]] = None
    required_previous_services: Optional[List[str]] = None
    state_manager_method: Optional[str] = None
    tags: Optional[List[str]] = None
    host: Optional[str] = None
    port: Optional[int] = None
    endpoint: Optional[str] = None


class PipelineConfService(PipelineConfServiceComponent):
    is_enabled: Optional[bool] = True
    source: PipelineConfComponentSource


class PipelineConfServiceList(BaseModelNoExtra):
    last_chance_service: Optional[PipelineConfService] = None
    timeout_service: Optional[PipelineConfService] = None
    annotators: Dict[str, PipelineConfService]
    response_annotators: Optional[Dict[str, PipelineConfService]] = None
    response_annotator_selectors: Optional[PipelineConfService] = None
    candidate_annotators: Optional[Dict[str, PipelineConfService]] = None
    skill_selectors: Optional[Dict[str, PipelineConfService]] = None
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


class PipelineConfMetadata(BaseModelNoExtra, DateCreatedFieldMixin):
    display_name: str
    author: str
    description: str

    # subject to deprecation:
    version: Optional[str] = None
    ram_usage: Optional[str] = None
    gpu_usage: Optional[str] = None
    disk_usage: Optional[str] = None


class PipelineConf(BaseModelNoExtra):
    """
    Implements pipeline.json config structure
    """

    connectors: Optional[Dict[str, PipelineConfConnector]] = None
    services: PipelineConfServiceList
    metadata: Optional[PipelineConfMetadata] = None


class ContainerBuildDefinition(BaseModelNoExtra):
    args: Optional[Dict[str, Any]] = None
    context: Optional[Path] = None
    dockerfile: Optional[Path] = None


class DeploymentDefinitionResourcesArg(BaseModelNoExtra):
    memory: str

    @field_validator("memory")
    @classmethod
    def check_memory_format(cls, v):
        check_memory_format(v)
        return v


class DeploymentDefinitionResources(BaseModelNoExtra):
    limits: DeploymentDefinitionResourcesArg
    reservations: DeploymentDefinitionResourcesArg


class DeploymentDefinition(BaseModelNoExtra):
    mode: Optional[str] = None
    replicas: Optional[int] = None
    resources: Optional[DeploymentDefinitionResources] = None


class ComposeContainer(BaseModelNoExtra):
    image: Optional[str] = None
    volumes: Optional[List[str]] = None
    env_file: Optional[Union[list, str]] = None
    build: Optional[ContainerBuildDefinition] = None
    command: Optional[Union[list, str]] = None
    environment: Optional[Union[Dict[str, Any], list]] = None
    deploy: Optional[DeploymentDefinition] = None
    tty: Optional[bool] = None
    ports: Optional[List[str]] = None


class ComposeDevContainer(BaseModelNoExtra):
    volumes: Optional[List[str]] = None
    ports: List[str]


class ComposeLocalContainer(ComposeContainer, ComposeDevContainer):
    ports: Optional[List[str]] = None


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


# NEW
class Service(BaseModelNoExtra):
    name: str
    endpoints: list
    compose: Optional[ComposeContainer] = None
    proxy: Optional[ComposeContainer] = None


class ComponentEndpoint(BaseModelNoExtra):
    group: str
    endpoint: str


class ComponentTemplate(BaseModelNoExtra):
    name: str
    display_name: str
    author: EmailStr
    description: str
    endpoints: List[ComponentEndpoint]
    config_keys: Optional[dict] = None


class Component(BaseModelNoExtra, DateCreatedFieldMixin):
    # template: Optional[ComponentTemplate]
    name: str
    display_name: str
    component_type: Optional[COMPONENT_TYPES] = None
    model_type: Optional[MODEL_TYPES] = None
    is_customizable: bool
    author: EmailStr
    description: str
    ram_usage: Optional[str] = None
    gpu_usage: Optional[str] = None

    group: Optional[str] = None
    connector: Union[str, PipelineConfConnector]
    dialog_formatter: Optional[Union[str, dict]] = None
    response_formatter: Optional[str] = None
    previous_services: Optional[List[str]] = None
    required_previous_services: Optional[List[str]] = None
    state_manager_method: Optional[str] = None
    tags: Optional[List[str]] = None
    endpoint: Optional[str] = None

    service: Path

    @field_validator("ram_usage", "gpu_usage")
    @classmethod
    def check_memory_format(cls, v):
        check_memory_format(v)
        return v


AnyContainer = Union[ComposeContainer, ComposeDevContainer, ComposeLocalContainer]
AnyComposeConfig = Union[ComposeOverride, ComposeDev, ComposeProxy, ComposeLocal]
AnyConfig = Union[PipelineConf, ComposeOverride, ComposeDev, ComposeProxy, ComposeLocal]
AnyConfigType = Type[Union[PipelineConf, ComposeOverride, ComposeDev, ComposeProxy, ComposeLocal]]
