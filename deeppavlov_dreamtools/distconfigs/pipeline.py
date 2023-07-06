import itertools
import json
from pathlib import Path
from typing import Dict, Optional, Union, Iterable, Tuple, List

from deeppavlov_dreamtools import utils
from deeppavlov_dreamtools.distconfigs import generics
from deeppavlov_dreamtools.distconfigs.components import DreamComponent
from deeppavlov_dreamtools.distconfigs.generics import PipelineConfMetadata, PipelineConf, Component
from deeppavlov_dreamtools.distconfigs.services import DreamService


class Pipeline:
    FILE_NAME = "pipeline_conf.json"
    SINGLE_COMPONENT_GROUPS = [
        "last_chance_service",
        "timeout_service",
        "response_annotator_selectors",
    ]
    MULTIPLE_COMPONENT_GROUPS = [
        "annotators",
        "response_annotators",
        "candidate_annotators",
        "skill_selectors",
        "skills",
        "response_selectors",
    ]
    COMPONENT_GROUPS = [
        "last_chance_service",
        "timeout_service",
        "annotators",
        "response_annotators",
        "response_annotator_selectors",
        "candidate_annotators",
        "skill_selectors",
        "skills",
        "response_selectors",
    ]

    def __init__(
        self,
        config: generics.PipelineConf,
        metadata: PipelineConfMetadata,
        annotators: Dict[str, DreamComponent],
        skills: Dict[str, DreamComponent],
        response_selectors: Dict[str, DreamComponent],
        last_chance_service: Optional[DreamComponent] = None,
        timeout_service: Optional[DreamComponent] = None,
        response_annotators: Optional[Dict[str, DreamComponent]] = None,
        response_annotator_selectors: Optional[DreamComponent] = None,
        candidate_annotators: Optional[Dict[str, DreamComponent]] = None,
        skill_selectors: Optional[Dict[str, DreamComponent]] = None,
        services: Optional[Dict[str, DreamComponent]] = None,
    ):
        self._config = config
        self.metadata = metadata

        self.agent = self.validate_agent_services(last_chance_service, timeout_service)

        self.last_chance_service = last_chance_service
        self.timeout_service = timeout_service
        self.annotators = annotators
        self.response_annotators = response_annotators
        self.response_annotator_selectors = response_annotator_selectors
        self.candidate_annotators = candidate_annotators
        self.skill_selectors = skill_selectors
        self.skills = skills
        self.response_selectors = response_selectors
        self.services = services or {}

    @staticmethod
    def validate_agent_services(*args: DreamComponent):
        for a, b in itertools.combinations(args, 2):
            if a.service.service != b.service.service:
                raise ValueError(f"{a.component_file} != {b.component_file}")

        return args[0]

    def _update_agent_wait_hosts(self, wait_hosts: List[str]):
        self.agent.service.set_environment_value("WAIT_HOSTS", ", ".join(wait_hosts))

    def _update_prompt_selector(self):
        prompts_to_consider = []

        for name, component in self.iter_component_group("skills"):
            if component.service.environment.get("PROMPT_FILE"):
                prompt_name = Path(component.service.environment["PROMPT_FILE"]).stem
                prompts_to_consider.append(prompt_name)

        self.annotators["prompt_selector"].service.set_environment_value(
            "PROMPTS_TO_CONSIDER", ",".join(prompts_to_consider)
        )

    def iter_component_group(self, group: str):
        if group in self.SINGLE_COMPONENT_GROUPS:
            yield None, getattr(self, group)
        elif group in self.MULTIPLE_COMPONENT_GROUPS:
            for name, component in getattr(self, group).items():
                yield name, component

    def iter_components(self) -> Tuple[str, Optional[str], DreamComponent]:
        for group in self.COMPONENT_GROUPS:
            for name, component in self.iter_component_group(group):
                yield group, name, component

    # def assign_ports(self, available_ports: Iterable):
    #     for group, name, component in self.iter_components():
    #         if name:
    #             getattr(self, group)["name"].

    def generate_pipeline_conf(self) -> generics.PipelineConf:
        pipeline_conf = generics.PipelineConf(services=self.components, metadata=self.metadata)
        self._config = pipeline_conf

        return pipeline_conf

    def generate_compose(self) -> generics.ComposeOverride:
        all_services = {}
        all_ports = {}

        for group, name, component in self.iter_components():
            try:
                connector_url = component.component.connector.url
                host, port, _ = utils.parse_connector_url(connector_url)
            except (ValueError, AttributeError):
                host, port = "agent", None

            all_services[host] = component.service.generate_compose()
            all_ports[host] = port

        if self.services:
            for name, component in self.services.items():
                connector_url = component.component.connector.url
                host, port, _ = utils.parse_connector_url(connector_url)
                all_services[host] = component.service.generate_compose()
                all_ports[host] = port

        wait_hosts = [f"{h}:{p}" for h, p in all_ports.items() if h != "agent"]
        self._update_agent_wait_hosts(wait_hosts)
        all_services["agent"] = self.agent.service.generate_compose()
        compose = generics.ComposeOverride(services=all_services)
        return compose

    @classmethod
    def from_file(cls, path: Union[Path, str]):
        dream_root = Path(path).parents[2]
        data = utils.load_json(path)

        config = generics.PipelineConf.parse_obj(data)
        kwargs = {}

        for group_name in cls.COMPONENT_GROUPS:
            group = getattr(config.services, group_name, None)

            if group is None:
                continue

            group_components = {}
            try:
                for component_name, component in group.items():
                    component_obj = DreamComponent.from_file(component.source.component, dream_root)
                    group_components[component_name] = component_obj

            except AttributeError:
                component_obj = DreamComponent.from_file(group.source.component, dream_root)
                group_components = component_obj
            finally:
                kwargs[group_name] = group_components

        return cls(
            config=config,
            metadata=config.metadata,
            **kwargs,
        )

    def to_file(self, path: Union[Path, str], overwrite: bool = False):
        config = utils.pydantic_to_dict(self._config, exclude_none=True)
        return utils.dump_json(config, path, overwrite)

    @classmethod
    def from_dist(cls, dist_path: Union[str, Path]):
        """
        Loads config with default name from Dream distribution path

        Args:
            dist_path: path to Dream distribution

        Returns:
            Dream config instance

        """

        return cls.from_file(Path(dist_path).resolve() / cls.FILE_NAME)

    def to_dist(self, dist_path: Union[str, Path], overwrite: bool = False):
        """Saves config with default name to Dream distribution path

        Args:
            dist_path: path to Dream distribution
            overwrite: if True, overwrites existing file

        Returns:
            path to config file

        """

        path = Path(dist_path) / self.FILE_NAME
        return self.to_file(path, overwrite)

    @classmethod
    def from_name(cls, name: str, dream_root: Union[str, Path]):
        """
        Loads config with default name from Dream distribution path

        Args:
            name: Dream distribution name.
            dream_root: Dream root path.

        Returns:
            Dream config instance

        """

        dist_path = utils.resolve_dist_path(name, dream_root)

        return cls.from_file(dist_path / cls.FILE_NAME)

    def to_name(self, name: str, dream_root: Union[str, Path], overwrite: bool = False):
        """Saves config with default name to Dream distribution path

        Args:
            name: Dream distribution name.
            dream_root: Dream root path.
            overwrite: if True, overwrites existing file

        Returns:
            path to config file

        """

        dist_path = utils.resolve_dist_path(name, dream_root)
        return self.to_file(dist_path / self.FILE_NAME)

    @property
    def components(self) -> Dict[str, Union[Dict[str, generics.Component], generics.Component]]:
        return {
            "last_chance_service": getattr(self.last_chance_service, "pipeline", {}),
            "timeout_service": getattr(self.timeout_service, "pipeline", {}),
            "annotators": {name: item.pipeline for name, item in self.annotators.items()},
            "response_annotators": {name: item.pipeline for name, item in self.response_annotators.items()},
            "response_annotator_selectors": getattr(self.response_annotator_selectors, "pipeline", {}),
            "candidate_annotators": {name: item.pipeline for name, item in self.candidate_annotators.items()},
            "skill_selectors": {name: item.pipeline for name, item in self.skill_selectors.items()},
            "skills": {name: item.pipeline for name, item in self.skills.items()},
            "response_selectors": {name: item.pipeline for name, item in self.response_selectors.items()},
        }

    def get_component(self, group: str, name: str) -> DreamComponent:
        return getattr(self, group)[name]

    def add_component(self, component: DreamComponent):
        component_group = getattr(self, component.component.group)

        if component_group in self.SINGLE_COMPONENT_GROUPS:
            raise NotImplementedError(
                f"You cannot currently add components to {', '.join(self.SINGLE_COMPONENT_GROUPS)}"
            )

        component_group[component.component.name] = component
        setattr(self, component.component.group, component_group)

    def add_generative_prompted_skill(self, component: DreamComponent):
        self.skills[component.component.name] = component
        self._update_prompt_selector()

    def remove_component(self, group: str, name: str):
        component_group = getattr(self, group)

        if component_group in self.SINGLE_COMPONENT_GROUPS:
            raise NotImplementedError(
                f"You cannot currently remove components from {', '.join(self.SINGLE_COMPONENT_GROUPS)}"
            )

        del component_group[name]
        setattr(self, group, component_group)

    def remove_generative_prompted_skill(self, name: str):
        del self.skills[name]
        self._update_prompt_selector()
