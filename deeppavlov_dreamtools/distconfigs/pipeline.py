import json
from pathlib import Path
from typing import Dict, Optional, Union

from deeppavlov_dreamtools import utils
from deeppavlov_dreamtools.distconfigs.components import DreamComponent
from deeppavlov_dreamtools.distconfigs.generics import PipelineConfMetadata, PipelineConfModel, Component


class Pipeline:

    FILE_NAME = "pipeline_conf.json"
    SERVICE_GROUPS = [
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
        config,
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
    ):
        self._config = config
        self.metadata = metadata

        self.last_chance_service = last_chance_service
        self.timeout_service = timeout_service
        self.annotators = annotators
        self.response_annotators = response_annotators
        self.response_annotator_selectors = response_annotator_selectors
        self.candidate_annotators = candidate_annotators
        self.skill_selectors = skill_selectors
        self.skills = skills
        self.response_selectors = response_selectors

    @classmethod
    def from_file(cls, path: Union[Path, str]):
        dream_root = Path(path).parents[2]
        data = utils.load_json(path)

        config = PipelineConfModel.parse_obj(data)
        kwargs = {}

        for group_name in cls.SERVICE_GROUPS:
            group = getattr(config.services, group_name, None)

            if group is None:
                continue

            group_components = {}
            try:
                for component_name, component in group.items():
                    # TODO remove condition when empty agent components are fixed
                    if component.source.directory != Path():
                        component_obj = DreamComponent.from_component_dir(
                            dream_root / component.source.directory,
                            component.source.container,
                            group_name,
                            component.source.endpoint
                        )
                        group_components[component_name] = component_obj

            except AttributeError:
                # TODO remove condition when empty agent components are fixed
                if group.source.directory != Path():
                    component_obj = DreamComponent.from_component_dir(
                        dream_root / group.source.directory,
                        group.source.container,
                        group_name,
                        group.source.endpoint
                    )
                    group_components = component_obj
            finally:
                kwargs[group_name] = group_components

        return cls(
            config=config,
            metadata=config.metadata,
            **kwargs,
        )

    def to_file(self, path: Union[Path, str], overwrite: bool = False):
        # Until .dict() with jsonable type serialization is implemented
        # we will have to use this workaround
        # https://github.com/samuelcolvin/pydantic/issues/1409
        config = json.loads(self._config.json(exclude_none=True))
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
    def components(self) -> Dict[str, Union[Dict[str, Component], Component]]:
        return {
            "last_chance_service": getattr(self.last_chance_service, "config", {}),
            "timeout_service": getattr(self.timeout_service, "config", {}),
            "annotators": {name: item.config for name, item in self.annotators.items()},
            "response_annotators": {name: item.config for name, item in self.response_annotators.items()},
            "response_annotator_selectors": getattr(self.response_annotator_selectors, "config", {}),
            "candidate_annotators": {name: item.config for name, item in self.candidate_annotators.items()},
            "skill_selectors": {name: item.config for name, item in self.skill_selectors.items()},
            "skills": {name: item.config for name, item in self.skills.items()},
            "response_selectors": {name: item.config for name, item in self.response_selectors.items()},
        }
