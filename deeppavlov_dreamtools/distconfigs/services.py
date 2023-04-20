from pathlib import Path
from typing import Union

from deeppavlov_dreamtools import utils
from deeppavlov_dreamtools.distconfigs import generics


class DreamService:
    def __init__(
        self,
        source_dir: Union[Path, str],
        config_dir: Union[Path, str],
        service_file: Union[Path, str],
        environment_file: Union[Path, str],
        service: generics.Service,
        environment: dict,
    ):
        self.source_dir = source_dir
        self.config_dir = config_dir

        self.service_file = service_file
        self.environment_file = environment_file

        self.service = service
        self.environment = environment

    @classmethod
    def from_source_dir(cls, path: Union[Path, str], config_name: str):
        source_dir = Path(path)
        config_dir = source_dir / "service_configs" / config_name

        service_file = config_dir / "service.yml"
        environment_file = config_dir / "environment.yml"

        service = generics.Service(**utils.load_yml(service_file))
        environment = utils.load_yml(environment_file)

        return cls(source_dir, config_dir, service_file, environment_file, service, environment)

    def save_service_config(self):
        utils.dump_yml(utils.pydantic_to_dict(self.service), self.service_file, overwrite=True)

    def save_environment_config(self):
        utils.dump_yml(self.environment, self.environment_file, overwrite=True)

    def save_configs(self):
        self.save_service_config()
        self.save_environment_config()

    def set_environment_value(self, key: str, value: str):
        self.environment[key] = value
        self.save_environment_config()
