from pathlib import Path
from typing import Union

from deeppavlov_dreamtools import utils
from deeppavlov_dreamtools.distconfigs import generics


def _resolve_default_service_config_paths(
    config_dir: Union[Path, str] = None, source_dir: Union[Path, str] = None, config_name: str = None
):
    if config_dir:
        config_dir = Path(config_dir)
        source_dir = config_dir.parents[1]
    elif source_dir and config_name:
        source_dir = Path(source_dir)
        config_dir = source_dir / "service_configs" / config_name
    else:
        raise ValueError(f"Provide either 'config_dir' or 'source_dir' and 'name'")

    service_file = config_dir / "service.yml"
    environment_file = config_dir / "environment.yml"

    return source_dir, config_dir, service_file, environment_file


def create_agent_service(
    dream_root: Union[Path, str], config_dir: Union[Path, str], service_name: str, assistant_dist_pipeline_file: Union[Path, str]
):
    source_dir, config_dir, service_file, environment_file = _resolve_default_service_config_paths(
        config_dir=config_dir
    )
    service = DreamService(
        dream_root,
        source_dir,
        config_dir,
        service_file,
        environment_file,
        service=generics.Service(
            name=service_name,
            endpoints=["respond"],
            compose=generics.ComposeContainer(
                # env_file=[".env"],
                command=(
                    f"sh -c 'bin/wait && python -m deeppavlov_agent.run "
                    f"agent.pipeline_config={assistant_dist_pipeline_file}'"
                ),
                volumes=[".:/dp-agent"],
            ),
        ),
        environment={
            "WAIT_HOSTS": "",
            "WAIT_HOSTS_TIMEOUT": "${WAIT_TIMEOUT:-480}",
            "HIGH_PRIORITY_INTENTS": "1",
            "RESTRICTION_FOR_SENSITIVE_CASE": "1",
            "ALWAYS_TURN_ON_ALL_SKILLS": "0",
            "LANGUAGE": "EN",
        },
    )
    service.save_configs()

    return service


def create_generative_prompted_skill_service(
    dream_root: Union[Path, str], config_dir: Union[Path, str], service_name: str, generative_service_model: str
):
    source_dir, config_dir, service_file, environment_file = _resolve_default_service_config_paths(
        config_dir=config_dir
    )
    service = DreamService(
        dream_root,
        source_dir,
        config_dir,
        service_file,
        environment_file,
        service=generics.Service(
            name=service_name,
            endpoints=["respond"],
            compose=generics.ComposeContainer(
                env_file=[".env"],
                build=generics.ContainerBuildDefinition(
                    context=".", dockerfile="./skills/dff_template_prompted_skill/Dockerfile"
                ),
                deploy=generics.DeploymentDefinition(
                    resources=generics.DeploymentDefinitionResources(
                        limits=generics.DeploymentDefinitionResourcesArg(memory="128M"),
                        reservations=generics.DeploymentDefinitionResourcesArg(memory="128M"),
                    )
                ),
                volumes=["./skills/dff_template_prompted_skill:/src", "./common:/src/common"],
            ),
        ),
        environment={
            "SERVICE_NAME": service_name,
            "PROMPT_FILE": f"common/prompts/{service_name}.json",
            "GENERATIVE_SERVICE_URL": f"http://{generative_service_model}:8146/respond",
            "GENERATIVE_SERVICE_CONFIG": "default_generative_config.json",
            "GENERATIVE_TIMEOUT": 5,
            "N_UTTERANCES_CONTEXT": 3,
        },
    )
    service.save_configs()

    return service


class DreamService:
    def __init__(
        self,
        dream_root: Union[Path, str],
        source_dir: Union[Path, str],
        config_dir: Union[Path, str],
        service_file: Union[Path, str],
        environment_file: Union[Path, str],
        service: generics.Service,
        environment: dict,
    ):
        self.dream_root = dream_root
        self.source_dir = source_dir
        self.config_dir = config_dir

        self.service_file = service_file
        self.environment_file = environment_file

        self.service = service
        self.environment = environment

    @classmethod
    def from_source_dir(cls, dream_root: Union[Path, str],  path: Union[Path, str], config_name: str):
        source_dir, config_dir, service_file, environment_file = _resolve_default_service_config_paths(
            source_dir=path, config_name=config_name
        )

        service = generics.Service(**utils.load_yml(service_file))
        environment = utils.load_yml(environment_file)

        return cls(dream_root, source_dir, config_dir, service_file, environment_file, service, environment)

    @classmethod
    def from_config_dir(cls, dream_root: Union[Path, str], path: Union[Path, str]):
        source_dir, config_dir, service_file, environment_file = _resolve_default_service_config_paths(config_dir=path)

        service = generics.Service(**utils.load_yml(service_file))
        environment = utils.load_yml(environment_file)

        return cls(dream_root, source_dir, config_dir, service_file, environment_file, service, environment)

    def _create_config_dir(self):
        config_dir = self.dream_root / self.config_dir
        config_dir.mkdir(parents=True, exist_ok=True)

    def save_service_config(self):
        self._create_config_dir()
        utils.dump_yml(utils.pydantic_to_dict(self.service), self.dream_root / self.service_file, overwrite=True)

    def save_environment_config(self):
        self._create_config_dir()
        utils.dump_yml(self.environment, self.dream_root / self.environment_file, overwrite=True)

    def save_configs(self):
        self.save_service_config()
        self.save_environment_config()

    def set_environment_value(self, key: str, value: str):
        self.environment[key] = value
        self.save_environment_config()
