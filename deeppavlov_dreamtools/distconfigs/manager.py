import json
import re
from pathlib import Path
from shutil import copytree
from typing import Union, Any, Optional, Tuple, Dict

import yaml

from deeppavlov_dreamtools.distconfigs.generics import (
    PipelineConf,
    ComposeOverride,
    ComposeDev,
    ComposeProxy,
    AnyConfig,
    AnyConfigType,
    PipelineConfServiceList,
    PipelineConfService,
    PipelineConfConnector,
    ComposeContainer,
    ComposeDevContainer,
    AnyContainer,
    ComposeLocal,
    DeploymentDefinition,
    ComposeLocalContainer,
    ContainerBuildDefinition,
    DeploymentDefinitionResources,
    DeploymentDefinitionResourcesArg,
)
from deeppavlov_dreamtools.distconfigs import const


def _parse_connector_url(
    url: Optional[str] = None,
) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """
    Deserializes a string into host, port, endpoint components.

    Args:
        url: Full url string of format http(s)://{host}:{port}/{endpoint}.
            If empty, returns (None, None, None)

    Returns:
        tuple of (host, port, endpoint)

    """
    host = port = endpoint = None
    if url:
        url_without_protocol = url.split("//")[-1]
        url_parts = url_without_protocol.split("/", maxsplit=1)

        host, port = url_parts[0].split(":")
        endpoint = ""

        if len(url_parts) > 1:
            endpoint = url_parts[1]

    return host, port, endpoint


class BaseDreamConfig:
    """
    Base class which wraps a generic config model.

    Implements basic loaders and dumpers and defines constant class attributes.
    """

    DEFAULT_FILE_NAME: str
    GENERIC_MODEL: AnyConfig

    def __init__(self, config: AnyConfig):
        self.config = config

    @staticmethod
    def load(path: Union[Path, str]):
        raise NotImplementedError("Override this function")

    @staticmethod
    def dump(data: Any, path: Union[Path, str], overwrite: bool = False) -> Path:
        raise NotImplementedError("Override this function")

    @classmethod
    def from_path(cls, path: Union[str, Path]):
        """
        Loads config from file path

        Args:
            path: path to config file

        Returns:
            Dream config instance

        """
        data = cls.load(path)
        config = cls.GENERIC_MODEL.parse_obj(data)
        return cls(config)

    def to_path(self, path: Union[str, Path], overwrite: bool = False):
        """
        Saves config to file path

        Args:
            path: path to config file
            overwrite: if True, overwrites existing file

        Returns:
            path to config file

        """

        # Until .dict() with jsonable type serialization is implemented
        # we will have to use this workaround
        # https://github.com/samuelcolvin/pydantic/issues/1409
        config = json.loads(self.config.json(exclude_none=True))
        return self.dump(config, path, overwrite)

    @classmethod
    def from_dist(cls, dist_path: Union[str, Path]):
        """
        Loads config with default name from Dream distribution path

        Args:
            dist_path: path to Dream distribution

        Returns:
            Dream config instance

        """

        data = cls.load(Path(dist_path).resolve() / cls.DEFAULT_FILE_NAME)
        config = cls.GENERIC_MODEL.parse_obj(data)
        return cls(config)

    def to_dist(self, dist_path: Union[str, Path], overwrite: bool = False):
        """Saves config with default name to Dream distribution path

        Args:
            dist_path: path to Dream distribution
            overwrite: if True, overwrites existing file

        Returns:
            path to config file

        """

        # Until .dict() with jsonable type serialization is implemented
        # we will have to use this workaround
        # https://github.com/samuelcolvin/pydantic/issues/1409
        config = json.loads(self.config.json(exclude_none=True))
        path = Path(dist_path) / self.DEFAULT_FILE_NAME
        return self.dump(config, path, overwrite)

    def filter_services(self, include_names: list):
        """
        Filters services by name

        Args:
            include_names: only services with these names will be included

        Returns:

        """
        raise NotImplementedError("Override this function")


class JsonDreamConfig(BaseDreamConfig):
    """
    Base class which wraps a JSON config model.

    Implements or overrides common methods for JSON configs.
    """

    @staticmethod
    def load(path: Union[Path, str]):
        with open(path, "r", encoding="utf-8") as json_f:
            data = json.load(json_f)

        return data

    @staticmethod
    def dump(data: Any, path: Union[Path, str], overwrite: bool = False):
        mode = "w" if overwrite else "x"
        with open(path, mode, encoding="utf-8") as yml_f:
            json.dump(data, yml_f, indent=4)

        return path

    def filter_services(self, include_names: list):
        raise NotImplementedError("Override this function")


class YmlDreamConfig(BaseDreamConfig):
    """
    Base class which wraps a YML config model.

    Implements or overrides common methods for YML configs.
    """

    @staticmethod
    def load(path: Union[Path, str]):
        with open(path, "r", encoding="utf-8") as yml_f:
            data = yaml.load(yml_f, yaml.FullLoader)

        return data

    @staticmethod
    def dump(data: Any, path: Union[Path, str], overwrite: bool = False):
        mode = "w" if overwrite else "x"
        with open(path, mode, encoding="utf-8") as yml_f:
            yaml.dump(data, yml_f)

        return path

    def __getitem__(self, item) -> AnyContainer:
        return self.config.services[item]

    def iter_services(self):
        for s_name, s_definition in self.config.services.items():
            yield s_name, s_definition

    def filter_services(self, names: list):
        model_dict = {
            "version": self.config.version,
            "services": {k: v for k, v in self.config.services.items() if k in names},
        }
        config = self.GENERIC_MODEL.parse_obj(model_dict)
        return names, self.__class__(config)

    def add_service(self, name: str, definition: AnyContainer, inplace: bool = False):
        """
        Adds service to config

        Args:
            name: service name
            definition: generic service object
            inplace: if True, updates the config instance, returns a new copy of config instance otherwise

        Returns:
            config instance
        """
        services = self.config.copy().services
        services[name] = definition

        model_dict = {
            "version": self.config.version,
            "services": services,
        }
        config = self.GENERIC_MODEL.parse_obj(model_dict)
        if inplace:
            self.config = config
            value = self
        else:
            value = self.__class__(config)
        return value

    def remove_service(self, name: str, inplace: bool = False):
        """
        Removes service from config.

        Args:
            name: service name
            inplace: if True, updates the config instance, returns a new copy of config instance otherwise
        Returns:
            config instance
        """
        services = self.config.copy().services

        try:
            del services[name]
        except KeyError:
            raise KeyError(f"{name} is not in the service list")

        model_dict = {
            "version": self.config.version,
            "services": services,
        }
        config = self.GENERIC_MODEL.parse_obj(model_dict)
        if inplace:
            self.config = config
            value = self
        else:
            value = self.__class__(config)
        return value


class DreamPipeline(JsonDreamConfig):
    """
    Main class which wraps a ``pipeline_conf.json`` config model.

    Implements or overrides methods specific to the pipeline config.
    """

    DEFAULT_FILE_NAME = "pipeline_conf.json"
    GENERIC_MODEL = PipelineConf

    # @property
    # def container_names(self):
    #     for s in self._config.services.flattened_dict.values():
    #         host, _, _ = _parse_connector_url(s.connector_url)
    #         if host:
    #             yield host

    # def discover_host_port_endpoint(self, service: str):
    #     try:
    #         url = self._config.services.flattened_dict[service].connector_url
    #         host, port, endpoint = _parse_connector_url(url)
    #     except KeyError:
    #         raise KeyError(f"{service} not found in pipeline!")
    #
    #     return host, port, endpoint

    def _filter_services_by_name(self, names: list):
        for service_group in self.config.services.editable_groups:
            for service_name, service in getattr(self.config.services, service_group).items():
                if hasattr(service.connector, "url"):
                    url = service.connector.url
                    if url:
                        host, port, endpoint = _parse_connector_url(url)
                        if host in names:
                            yield service_group, service_name, service
                else:
                    service_name = service_name.replace("_", "-")
                    if service_name in names:
                        yield service_group, service_name, service

    def _recursively_parse_requirements(self, service: PipelineConfService):
        previous_services = service.previous_services or []
        required_previous_services = service.required_previous_services or []

        for required_service_name in previous_services + required_previous_services:
            required_service_parts = required_service_name.split(".", maxsplit=1)
            if len(required_service_parts) > 1:
                required_group, required_name = required_service_parts
                required_service = getattr(self.config.services, required_group)[required_name]
                yield required_group, required_name, required_service
                yield from self._recursively_parse_requirements(required_service)

    def filter_services(self, include_names: list):
        filtered_dict = {grp: {} for grp in self.config.services.editable_groups}
        include_names_extended = list(include_names).copy()

        for group, name, service in self._filter_services_by_name(include_names):
            filtered_dict[group][name] = service

            for (
                required_group,
                required_name,
                required_service,
            ) in self._recursively_parse_requirements(service):
                filtered_dict[required_group][required_name] = required_service
                include_names_extended.append(required_name)

        filtered_dict["last_chance_service"] = self.config.services.last_chance_service
        filtered_dict["timeout_service"] = self.config.services.timeout_service
        filtered_dict["bot_annotator_selector"] = self.config.services.bot_annotator_selector
        filtered_dict["skill_selectors"] = self.config.services.skill_selectors
        services = PipelineConfServiceList(**filtered_dict)

        model_dict = {
            "connectors": self.config.connectors,
            "services": services,
        }
        config = self.GENERIC_MODEL(**model_dict)
        return include_names_extended, self.__class__(config)

    def add_service(
        self,
        name: str,
        service_type: str,
        definition: PipelineConfService,
        inplace: bool = False,
    ):
        """
        Adds service to config

        Args:
            name: service name
            service_type: service type in pipeline
            definition: generic service object
            inplace: if True, updates the config instance, returns a new copy of config instance otherwise

        Returns:
            config instance
        """
        services = self.config.copy().services
        getattr(services, service_type)[name] = definition

        model_dict = {
            "connectors": self.config.connectors,
            "services": services,
        }
        config = self.GENERIC_MODEL.parse_obj(model_dict)
        if inplace:
            self.config = config
            value = self
        else:
            value = self.__class__(config)
        return value

    def remove_service(self, service_type: str, name: str, inplace: bool = False):
        """
        Removes service from config.

        Args:
            service_type: service type in pipeline
            name: service name
            inplace: if True, updates the config instance, returns a new copy of config instance otherwise
        Returns:
            config instance
        """
        # TODO implement recursive removal of dependent services
        services = self.config.copy().services

        try:
            del getattr(services, service_type)[name]
        except AttributeError:
            raise KeyError(f"{service_type} is not a valid service group")
        except KeyError:
            raise KeyError(f"{name} is not in the service list")

        model_dict = {
            "connectors": self.config.connectors,
            "services": services,
        }
        config = self.GENERIC_MODEL.parse_obj(model_dict)
        if inplace:
            self.config = config
            value = self
        else:
            value = self.__class__(config)
        return value


class DreamComposeOverride(YmlDreamConfig):
    """
    Main class which wraps a ``docker-compose.override.yml`` config model.

    Implements or overrides methods specific to the docker compose override config.
    """

    DEFAULT_FILE_NAME = "docker-compose.override.yml"
    GENERIC_MODEL = ComposeOverride


class DreamComposeDev(YmlDreamConfig):
    """
    Main class which wraps a ``dev.yml`` config model.

    Implements or overrides methods specific to the dev config.
    """

    DEFAULT_FILE_NAME = "dev.yml"
    GENERIC_MODEL = ComposeDev


class DreamComposeProxy(YmlDreamConfig):
    """
    Main class which wraps a ``proxy.yml`` config model.

    Implements or overrides methods specific to the proxy config.
    """

    DEFAULT_FILE_NAME = "proxy.yml"
    GENERIC_MODEL = ComposeProxy


class DreamComposeLocal(YmlDreamConfig):
    """
    Main class which wraps a ``local.yml`` config model.

    Implements or overrides methods specific to the local config.
    """

    DEFAULT_FILE_NAME = "local.yml"
    GENERIC_MODEL = ComposeLocal


AnyConfigClass = Union[
    DreamPipeline,
    DreamComposeOverride,
    DreamComposeDev,
    DreamComposeProxy,
    DreamComposeLocal,
]


class DreamDist:
    def __init__(
        self,
        dist_path: Union[str, Path],
        name: str,
        dream_root: Union[str, Path],
        pipeline_conf: DreamPipeline = None,
        compose_override: DreamComposeOverride = None,
        compose_dev: DreamComposeDev = None,
        compose_proxy: DreamComposeProxy = None,
        compose_local: DreamComposeLocal = None,
    ):
        """
        Instantiates a new DreamDist object

        Args:
            dist_path: path to Dream distribution
            name: name of Dream distribution
            dream_root: path to Dream root directory
            pipeline_conf: instance of DreamPipeline config
            compose_override: instance of DreamComposeOverride config
            compose_dev: instance of DreamComposeDev config
            compose_proxy: instance of DreamComposeProxy config
            compose_local: instance of DreamComposeLocal config
        """
        self._dist_path = Path(dist_path)
        self._name = name
        self.dream_root = dream_root
        self.pipeline_conf = pipeline_conf
        self.compose_override = compose_override
        self.compose_dev = compose_dev
        self.compose_proxy = compose_proxy
        self.compose_local = compose_local

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, new_name):
        self._dist_path = self._dist_path.parents[0] / new_name
        self._name = new_name

    @staticmethod
    def load_configs_with_default_filenames(
        dist_path: Union[str, Path],
        pipeline_conf: bool,
        compose_override: bool,
        compose_dev: bool,
        compose_proxy: bool,
        compose_local: bool,
    ) -> Dict[str, AnyConfigClass]:
        """
        Loads config objects using their default file names located under given Dream distribution path.

        Args:
            dist_path: path to Dream distribution
            pipeline_conf: if True, loads pipeline_conf.json
            compose_override: if True, loads docker-compose.override.yml
            compose_dev: if True, loads dev.yml
            compose_proxy: if True, loads proxy.yml
            compose_local: if True, loads local.yml

        Returns:
            dict with arg_names as keys, config_objects as values

        """
        kwargs = {}

        if pipeline_conf:
            kwargs["pipeline_conf"] = DreamPipeline.from_dist(dist_path)
        if compose_override:
            kwargs["compose_override"] = DreamComposeOverride.from_dist(dist_path)
        if compose_dev:
            kwargs["compose_dev"] = DreamComposeDev.from_dist(dist_path)
        if compose_proxy:
            kwargs["compose_proxy"] = DreamComposeProxy.from_dist(dist_path)
        if compose_local:
            kwargs["compose_local"] = DreamComposeLocal.from_dist(dist_path)

        return kwargs

    @staticmethod
    def resolve_all_paths(
        dist_path: Union[str, Path] = None,
        name: str = None,
        dream_root: Union[str, Path] = None,
    ):
        """
        Resolves path to Dream distribution, its name, and Dream root path
        from either ``dist_path`` or ``name`` and ``dream_root``.

        Args:
            dist_path: path to Dream distribution
            name: name of Dream distribution
            dream_root: path to Dream root directory

        Returns:
            tuple of (distribution path, distribution name, dream root path)

        Raises:
            ValueError: not enough arguments to resolve
            NotADirectoryError: dist_path is not a valid Dream distribution directory
        """
        if dist_path:
            name, dream_root = DreamDist.resolve_name_and_dream_root(dist_path)
        elif name and dream_root:
            dist_path = DreamDist.resolve_dist_path(name, dream_root)
        else:
            raise ValueError("Provide either dist_path or name and dream_root")

        if not dist_path.exists() and dist_path.is_dir():
            raise NotADirectoryError(f"{dist_path} is not a Dream distribution")

        return dist_path, name, dream_root

    @staticmethod
    def resolve_dist_path(name: str, dream_root: Union[str, Path]):
        """
        Resolves path to Dream distribution from name and Dream root path.

        Args:
            name: name of Dream distribution
            dream_root: path to Dream root directory

        Returns:
            path to Dream distribution

        """
        return Path(dream_root) / const.ASSISTANT_DISTS_DIR_NAME / name

    @staticmethod
    def resolve_name_and_dream_root(path: Union[str, Path]):
        """
        Resolves name and Dream root directory path from Dream distribution path.

        Args:
            path: path to Dream distribution

        Returns:
            tuple of (name of Dream distribution, path to Dream root directory)

        """
        path = Path(path)
        return path.name, path.parents[1]

    @classmethod
    def from_name(
        cls,
        name: str,
        dream_root: Union[str, Path],
        pipeline_conf: bool = True,
        compose_override: bool = True,
        compose_dev: bool = True,
        compose_proxy: bool = True,
        compose_local: bool = True,
    ):
        """
        Loads Dream distribution from ``name`` and ``dream_root`` path with default configs.

        Args:
            name: Dream distribution name.
            dream_root: Dream root path.
            pipeline_conf: load `pipeline_conf.json` inside ``path``
            compose_override: load `docker-compose.override.yml` inside ``path``
            compose_dev: load `dev.yml` inside ``path``
            compose_proxy: load `proxy.yml` inside ``path``
            compose_local: load `local.yml` inside ``path``

        Returns:
            instance of DreamDist
        """
        dist_path, name, dream_root = DreamDist.resolve_all_paths(name=name, dream_root=dream_root)
        cls_kwargs = cls.load_configs_with_default_filenames(
            dist_path,
            pipeline_conf,
            compose_override,
            compose_dev,
            compose_proxy,
            compose_local,
        )

        return cls(dist_path, name, dream_root, **cls_kwargs)

    @classmethod
    def from_dist(
        cls,
        dist_path: Union[str, Path] = None,
        pipeline_conf: bool = True,
        compose_override: bool = True,
        compose_dev: bool = True,
        compose_proxy: bool = True,
        compose_local: bool = True,
    ):
        """
        Loads Dream distribution from ``dist_path`` with default configs.

        Args:
            dist_path: path to Dream distribution, e.g. ``~/dream/assistant_dists/dream``.
            pipeline_conf: load `pipeline_conf.json` inside ``path``
            compose_override: load `docker-compose.override.yml` inside ``path``
            compose_dev: load `dev.yml` inside ``path``
            compose_proxy: load `proxy.yml` inside ``path``
            compose_local: load `local.yml` inside ``path``
        Returns:
            instance of DreamDist
        """
        dist_path, name, dream_root = DreamDist.resolve_all_paths(dist_path=dist_path)
        cls_kwargs = cls.load_configs_with_default_filenames(
            dist_path,
            pipeline_conf,
            compose_override,
            compose_dev,
            compose_proxy,
            compose_local,
        )

        return cls(dist_path, name, dream_root, **cls_kwargs)

    def create_dist(
        self,
        name: str,
        dream_root: Union[str, Path],
        service_names: Optional[list] = None,
        pipeline_conf: bool = True,
        compose_override: bool = True,
        compose_dev: bool = True,
        compose_proxy: bool = True,
        compose_local: bool = True,
    ):
        """
        Creates Dream distribution inherited from another distribution.

        The new distribution only has services included in ``service_names``.

        Args:
            name: name of new Dream distribution
            dream_root: path to Dream root directory
            service_names: list of services to be included in new distribution
            pipeline_conf: load `pipeline_conf.json` inside ``path``
            compose_override: load `docker-compose.override.yml` inside ``path``
            compose_dev: load `dev.yml` inside ``path``
            compose_proxy: load `proxy.yml` inside ``path``
            compose_local: load `local.yml` inside ``path``
        Returns:
            instance of DreamDist
        """
        new_compose_override = new_compose_dev = new_compose_proxy = new_compose_local = None
        all_names, new_pipeline_conf = self.pipeline_conf.filter_services(service_names)
        all_names += const.MANDATORY_SERVICES
        if compose_override:
            _, new_compose_override = self.compose_override.filter_services(all_names)

            new_agent_command = re.sub(
                f"assistant_dists/{self.name}/pipeline_conf.json",
                f"assistant_dists/{name}/pipeline_conf.json",
                new_compose_override.config.services["agent"].command,
            )
            new_compose_override.config.services["agent"].command = new_agent_command

            new_compose_override.config.services["agent"].environment["WAIT_HOSTS"] = ""
        if compose_dev:
            _, new_compose_dev = self.compose_dev.filter_services(all_names)
        if compose_proxy:
            _, new_compose_proxy = self.compose_proxy.filter_services(all_names)
        if compose_local:
            _, new_compose_local = self.compose_local.filter_services(all_names)

        return DreamDist(
            self.resolve_dist_path(name, dream_root),
            name,
            dream_root,
            new_pipeline_conf,
            new_compose_override,
            new_compose_dev,
            new_compose_proxy,
            new_compose_local,
        )

    def iter_loaded_configs(self):
        """
        Iterates over loaded config objects.

        Yields:
            config object

        """
        for config in [
            self.pipeline_conf,
            self.compose_override,
            self.compose_dev,
            self.compose_proxy,
            self.compose_local,
        ]:
            if config:
                yield config

    def save(self, overwrite: bool = False):
        """
        Dumps current config objects to files.

        Args:
            overwrite: if True, overwrites existing files

        Returns:
            list of paths to saved config files
        """
        paths = []

        self._dist_path.mkdir(parents=True, exist_ok=overwrite)
        for config in self.iter_loaded_configs():
            path = config.to_dist(self._dist_path, overwrite)
            paths.append(path)

        return paths

    def add_dff_skill(self, name: str, port: int):
        """
        Adds DFF skill to distribution.

        Args:
            name: DFF skill name
            port: port where new DFF skill should be deployed

        Returns:
            path to new DFF skill
        """
        name_with_underscores = name.replace("-", "_")
        name_with_dashes = name.replace("_", "-")

        skill_dir = Path(self.dream_root) / const.SKILLS_DIR_NAME / name
        if skill_dir.exists():
            raise FileExistsError(f"{skill_dir} already exists!")

        pkg_source_dir = Path(__file__).parents[1]
        dff_template_dir = pkg_source_dir / "static" / "dff_template_skill"
        copytree(dff_template_dir, skill_dir)

        if self.pipeline_conf:
            pl_service = PipelineConfService(
                connector=PipelineConfConnector(
                    protocol="http",
                    timeout=2,
                    url=f"http://{name_with_dashes}:{port}/respond",
                ),
                dialog_formatter=f"state_formatters.dp_formatters:{name}_formatter",
                response_formatter="state_formatters.dp_formatters:skill_with_attributes_formatter_service",
                previous_services=["skill_selectors"],
                state_manager_method="add_hypothesis",
            )
            self.pipeline_conf.add_service(name_with_underscores, "skills", pl_service, inplace=True)

        if self.compose_override:
            override_service = ComposeContainer(
                env_file=[".env"],
                build=ContainerBuildDefinition(
                    args={"SERVICE_PORT": port, "SERVICE_NAME": name},
                    context=Path("."),
                    dockerfile=skill_dir / "Dockerfile",
                ),
                command=f"gunicorn --workers=1 server:app -b 0.0.0.0:{port} --reload --timeout 500",
                deploy=DeploymentDefinition(
                    resources=DeploymentDefinitionResources(
                        limits=DeploymentDefinitionResourcesArg(memory="1G"),
                        reservations=DeploymentDefinitionResourcesArg(memory="1G"),
                    )
                ),
            )
            self.compose_override.add_service(name_with_dashes, override_service, inplace=True)

        if self.compose_dev:
            dev_service = ComposeDevContainer(
                volumes=[f"./skills/{name}:/src", "./common:/src/common"],
                ports=[f"{port}:{port}"],
            )
            self.compose_dev.add_service(name_with_dashes, dev_service, inplace=True)

        if self.compose_proxy:
            proxy_service = ComposeContainer(
                command=["nginx", "-g", "daemon off;"],
                build=ContainerBuildDefinition(context=Path("dp/proxy"), dockerfile=Path("Dockerfile")),
                environment=[f"PROXY_PASS=dream.deeppavlov.ai:{port}", f"PORT={port}"],
            )
            self.compose_proxy.add_service(name_with_dashes, proxy_service, inplace=True)

        self.save(True)

        return skill_dir

    def create_local_yml(
        self,
        services: list,
        drop_ports: bool = True,
        single_replica: bool = True,
    ):
        """
        Creates local config for distribution.

        Picks up container definitions from dev and proxy configs,
        replaces selected proxy services with their definitions from dev config,
        and dumps the resulting config to ``local.yml``

        Args:
            services: list of service names which should be deployed locally
            drop_ports: if True, removes port definitions from local services
            single_replica: if True, adds deployment arguments to all services

        Returns:
            path to new local config

        """
        services = list(services) + ["agent", "mongo"]

        dev_config_part = self.compose_dev.filter_services(services, inplace=False)
        proxy_config_part = self.compose_proxy.filter_services(exclude_names=services, inplace=False)
        local_config = DreamComposeLocal(ComposeLocal(services=proxy_config_part.config.services))
        all_config_parts = {
            **dev_config_part.config.services,
            **proxy_config_part.config.services,
        }

        for name, s in all_config_parts.items():
            if name in services:
                service = ComposeLocalContainer.parse_obj(s)
                if drop_ports:
                    service.ports = None
            else:
                service = s

            if single_replica:
                service.deploy = DeploymentDefinition(mode="replicated", replicas=1)

            local_config.add_service(name, service, inplace=True)
        return local_config.to_dist(self.dist_path)


def list_dists(dream_root: Union[Path, str]) -> list[DreamDist]:
    """
    Serializes configs from Dream assistant distributions to list of DreamDist objects

    Args:
        dream_root: path to Dream module

    Returns:
        dream_dists: python list of DreamDist objects

    """

    dist_path = Path(dream_root) / const.ASSISTANT_DISTS_DIR_NAME
    dream_dists = []
    distributions_paths = dist_path.iterdir()

    for distribution in distributions_paths:
        if distribution.is_file():
            continue
        filenames = [file.name for file in distribution.iterdir()]

        dream_dist = DreamDist.from_dist(
            distribution,
            pipeline_conf="pipeline_conf.json" in filenames,
            compose_override="docker-compose.override.yml" in filenames,
            compose_dev="dev.yml" in filenames,
            compose_proxy="proxy.yml" in filenames,
            compose_local="local.yml" in filenames,
        )
        dream_dists.append(dream_dist)

    return dream_dists
