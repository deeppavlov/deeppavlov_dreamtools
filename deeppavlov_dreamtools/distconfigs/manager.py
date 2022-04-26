import json
from pathlib import Path
from shutil import copytree
from typing import Union, Any, Optional, Tuple, Literal, Callable, Dict

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
)


def _parse_connector_url(
    url: Optional[str] = None,
) -> Tuple[Optional[str], Optional[str], Optional[str]]:
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
    DEFAULT_FILE_NAME: str
    GENERIC_MODEL: AnyConfig

    def __init__(self, config: AnyConfig):
        self._config = config

    @property
    def config(self):
        return self._config

    @staticmethod
    def load(path: Union[Path, str]):
        raise NotImplementedError("Override this function")

    @staticmethod
    def dump(data: Any, path: Union[Path, str], overwrite: bool = False):
        raise NotImplementedError("Override this function")

    @classmethod
    def from_path(cls, path: Union[str, Path]):
        """
        Load config from file path

        :param path: path to config file
        :return:
        """
        data = cls.load(path)
        config = cls.GENERIC_MODEL.parse_obj(**data)
        return cls(config)

    @classmethod
    def from_dist(cls, dist_path: Union[str, Path]):
        """
        Load config with default name from Dream distribution path

        :param dist_path: path to Dream distribution
        :return:
        """
        data = cls.load(Path(dist_path).resolve() / cls.DEFAULT_FILE_NAME)
        config = cls.GENERIC_MODEL.parse_obj(data)
        return cls(config)

    def to_path(self, path: Union[str, Path], overwrite: bool = False):
        """
        Save config to file path

        :param path: path to config file
        :param overwrite: if True, overwrites existing file
        :return:
        """
        # Until .dict() with jsonable type serialization is implemented
        # we will have to use this workaround
        # https://github.com/samuelcolvin/pydantic/issues/1409
        config = json.loads(self._config.json(exclude_none=True))
        return self.dump(config, path, overwrite)

    def to_dist(self, dist_path: Union[str, Path], overwrite: bool = False):
        """
        Save config to file path

        :param dist_path: path to Dream dist
        :param overwrite: if True, overwrites existing file
        :return:
        """
        # Until .dict() with jsonable type serialization is implemented
        # we will have to use this workaround
        # https://github.com/samuelcolvin/pydantic/issues/1409
        config = json.loads(self._config.json(exclude_none=True))
        path = Path(dist_path) / self.DEFAULT_FILE_NAME
        return self.dump(config, path, overwrite)

    def filter_services(
        self, include_names: list, exclude_names: list = None, inplace: bool = False
    ):
        raise NotImplementedError("Override this function")


class JsonDreamConfig(BaseDreamConfig):
    @staticmethod
    def load(path: Union[Path, str]):
        with open(path, "r", encoding="utf-8") as json_f:
            data = json.load(json_f)

        return data

    @staticmethod
    def dump(data: Any, path: Union[Path, str], overwrite: bool = False):
        mode = "x" if overwrite else "w"
        with open(path, mode, encoding="utf-8") as yml_f:
            json.dump(data, yml_f, indent=4)

        return path


class YmlDreamConfig(BaseDreamConfig):
    @staticmethod
    def load(path: Union[Path, str]):
        with open(path, "r", encoding="utf-8") as yml_f:
            data = yaml.load(yml_f, yaml.FullLoader)

        return data

    @staticmethod
    def dump(data: Any, path: Union[Path, str], overwrite: bool = False):
        mode = "x" if overwrite else "w"
        with open(path, mode, encoding="utf-8") as yml_f:
            yaml.dump(data, yml_f)

        return path

    def __getitem__(self, item) -> AnyContainer:
        return self._config.services[item]

    def iter_services(self):
        for s_name, s_definition in self._config.services.items():
            yield s_name, s_definition

    def add_service(self, name: str, definition: AnyContainer, inplace: bool = False):
        services = self._config.copy().services
        services[name] = definition

        model_dict = {
            "version": self._config.version,
            "services": services,
        }
        config = self.GENERIC_MODEL.parse_obj(model_dict)
        if inplace:
            self._config = config
            value = self
        else:
            value = self.__class__(config)
        return value


class DreamPipeline(JsonDreamConfig):
    DEFAULT_FILE_NAME = "pipeline_conf.json"
    GENERIC_MODEL = PipelineConf

    @property
    def container_names(self):
        for s in self._config.services.flattened_dict.values():
            host, _, _ = _parse_connector_url(s.connector_url)
            if host:
                yield host

    def discover_host_port_endpoint(self, service: str):
        try:
            url = self._config.services.flattened_dict[service].connector_url
            host, port, endpoint = _parse_connector_url(url)
        except KeyError:
            raise KeyError(f"{service} not found in pipeline!")

        return host, port, endpoint


class DreamComposeOverride(YmlDreamConfig):
    DEFAULT_FILE_NAME = "docker-compose.override.yml"
    GENERIC_MODEL = ComposeOverride


class DreamComposeDev(YmlDreamConfig):
    DEFAULT_FILE_NAME = "dev.yml"
    GENERIC_MODEL = ComposeDev


class DreamComposeProxy(YmlDreamConfig):
    DEFAULT_FILE_NAME = "proxy.yml"
    GENERIC_MODEL = ComposeProxy


class DreamComposeLocal(YmlDreamConfig):
    DEFAULT_FILE_NAME = "local.yml"
    GENERIC_MODEL = ComposeLocal


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
        self.dist_path = Path(dist_path)
        self.name = name
        self.dream_root = dream_root
        self.pipeline_conf = pipeline_conf
        self.compose_override = compose_override
        self.compose_dev = compose_dev
        self.compose_proxy = compose_proxy
        self.compose_local = compose_local

    @staticmethod
    def load_configs_with_default_filenames(
        dist_path: Union[str, Path],
        pipeline_conf: bool,
        compose_override: bool,
        compose_dev: bool,
        compose_proxy: bool,
        compose_local: bool,
        service_names: Optional[list] = None,
    ):
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

        if service_names:
            kwargs = {
                k: v.filter_services(service_names, inplace=True)
                for k, v in kwargs.items()
            }
        return kwargs

    @staticmethod
    def resolve_all_paths(
        dist_path: Union[str, Path] = None,
        name: str = None,
        dream_root: Union[str, Path] = None,
    ):
        """
        Resolve path to Dream distribution, its name, and Dream root path
        from either ``dist_path`` or ``name`` and ``dream_root``

        :param dist_path: Dream distribution path
        :param name: Dream distribution name
        :param dream_root: Dream root path
        :return:
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
        Resolve path to Dream distribution from name and Dream root path

        :param name: Dream distribution name
        :param dream_root: Dream root path
        :return:
        """
        return Path(dream_root) / "assistant_dists" / name

    @staticmethod
    def resolve_name_and_dream_root(path: Union[str, Path]):
        """
        Resolve name and Dream root directory path from Dream distribution path

        :param path: Dream distribution path
        :return:
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
        Load Dream distribution from ``name`` and ``dream_root`` path with default configs

        :param name: Dream distribution name.
        :param dream_root: Dream root path.
        :param pipeline_conf: load `pipeline_conf.json` inside ``path``
        :param compose_override: load `docker-compose.override.yml` inside ``path``
        :param compose_dev: load `dev.yml` inside ``path``
        :param compose_proxy: load `proxy.yml` inside ``path``
        :param compose_local: load `local.yml` inside ``path``
        :return: instance of DreamDist
        """
        dist_path, name, dream_root = DreamDist.resolve_all_paths(
            name=name, dream_root=dream_root
        )
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
        Load Dream distribution from ``dist_path`` with default configs

        :param dist_path: path to Dream distribution, e.g. ``~/dream/assistant_dists/dream``.
        :param pipeline_conf: load `pipeline_conf.json` inside ``path``
        :param compose_override: load `docker-compose.override.yml` inside ``path``
        :param compose_dev: load `dev.yml` inside ``path``
        :param compose_proxy: load `proxy.yml` inside ``path``
        :param compose_local: load `local.yml` inside ``path``
        :return: instance of DreamDist
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

    def iter_configs(self):
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
        paths = []

        self.dist_path.mkdir(parents=True, exist_ok=overwrite)
        for config in self.iter_configs():
            path = config.to_dist(self.dist_path, overwrite)
            paths.append(path)

        return paths
