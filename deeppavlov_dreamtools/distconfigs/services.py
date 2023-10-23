from pathlib import Path
from typing import Union, List, Literal, Optional

from pydantic import BaseModel

from deeppavlov_dreamtools import utils
from deeppavlov_dreamtools.distconfigs import generics


class ServicePrompt(BaseModel):
    prompt: Optional[str]
    goals: Optional[str]


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
    dream_root: Union[Path, str],
    config_dir: Union[Path, str],
    service_name: str,
    assistant_dist_pipeline_file: Union[Path, str],
    environment: dict = None,
    lang: Literal["en", "ru"] = "en"
):
    source_dir, config_dir, service_file, environment_file = _resolve_default_service_config_paths(
        config_dir=config_dir
    )

    if environment:
        environment["WAIT_HOSTS"] = ""
    else:
        environment = {
            "WAIT_HOSTS": "",
            "WAIT_HOSTS_TIMEOUT": "${WAIT_TIMEOUT:-480}",
            "HIGH_PRIORITY_INTENTS": 1,
            "RESTRICTION_FOR_SENSITIVE_CASE": 1,
            "ALWAYS_TURN_ON_ALL_SKILLS": 0,
            "LANGUAGE": lang.upper(),
            "FALLBACK_FILE": f"fallbacks_dream_{lang}.json",
        }

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
                deploy=generics.DeploymentDefinition(
                    resources=generics.DeploymentDefinitionResources(
                        limits=generics.DeploymentDefinitionResourcesArg(memory="200M"),
                        reservations=generics.DeploymentDefinitionResourcesArg(memory="200M"),
                    )
                ),
                volumes=[".:/dp-agent"],
            ),
        ),
        environment=environment,
    )
    service.save_configs()

    return service


def create_generative_prompted_skill_service(
    dream_root: Union[Path, str],
    config_dir: Union[Path, str],
    service_uid: str,
    service_name: str,
    service_port: int,
    generative_service_model: str,
    generative_service_port: int,
    generative_service_config: dict,
    prompt: str = None,
    prompt_goals: str = None,
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
            "SERVICE_PORT": service_port,
            "SERVICE_NAME": service_name,
            "PROMPT_FILE": f"common/prompts/{service_uid}.json",
            "GENERATIVE_SERVICE_URL": f"http://{generative_service_model}:{generative_service_port}/respond",
            "GENERATIVE_SERVICE_CONFIG": f"{service_uid}.json",
            "GENERATIVE_TIMEOUT": 120,
            "N_UTTERANCES_CONTEXT": 7,
            "ENVVARS_TO_SEND": "OPENAI_API_KEY,OPENAI_ORGANIZATION",
        },
    )

    service.dump_lm_config_file(generative_service_config)
    service.dump_prompt_file(prompt, prompt_goals)

    service.save_configs()

    return service


def create_prompt_selector_service(
    dream_root: Union[Path, str],
    config_dir: Union[Path, str],
    service_name: str,
    prompts_to_consider: List[str],
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
                    context=".",
                    dockerfile="./annotators/prompt_selector/Dockerfile",
                ),
                command="flask run -h 0.0.0.0 -p 8135",
                deploy=generics.DeploymentDefinition(
                    resources=generics.DeploymentDefinitionResources(
                        limits=generics.DeploymentDefinitionResourcesArg(memory="100M"),
                        reservations=generics.DeploymentDefinitionResourcesArg(memory="100M"),
                    )
                ),
                volumes=["./annotators/prompt_selector:/src", "./common:/src/common"],
                ports=["8135:8135"],
            ),
        ),
        environment={
            "SERVICE_PORT": 8135,
            "SERVICE_NAME": "prompt_selector",
            "N_SENTENCES_TO_RETURN": 3,
            "PROMPTS_TO_CONSIDER": ",".join(prompts_to_consider),
            "FLASK_APP": "server",
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
    def from_source_dir(cls, dream_root: Union[Path, str], path: Union[Path, str], config_name: str):
        source_dir, config_dir, service_file, environment_file = _resolve_default_service_config_paths(
            source_dir=path, config_name=config_name
        )

        service = generics.Service(**utils.load_yml(service_file))
        environment = utils.load_yml(environment_file)

        return cls(dream_root, source_dir, config_dir, service_file, environment_file, service, environment)

    @classmethod
    def from_config_dir(cls, dream_root: Union[Path, str], path: Union[Path, str]):
        source_dir, config_dir, service_file, environment_file = _resolve_default_service_config_paths(config_dir=path)

        service = generics.Service(**utils.load_yml(dream_root / service_file))
        environment = utils.load_yml(dream_root / environment_file)

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

    def get_environment_value(self, key: str):
        env_value = self.environment.get(key)
        if not env_value:
            raise ValueError(f"No {key} env provided in {self.environment_file}")

        return env_value

    def set_environment_value(self, key: str, value: str):
        self.environment[key] = value
        self.save_environment_config()

    def load_prompt_file(self):
        prompt_file = self.get_environment_value("PROMPT_FILE")
        prompt = utils.load_json(self.dream_root / prompt_file)

        return ServicePrompt(**prompt)

    def dump_prompt_file(self, prompt: str, goals: str):
        if prompt_file := self.get_environment_value("PROMPT_FILE"):
            utils.dump_json(
                ServicePrompt(prompt=prompt, goals=goals).dict(),
                self.dream_root / prompt_file,
                overwrite=True,
            )

    def load_lm_config_file(self):
        lm_config_file = self.get_environment_value("GENERATIVE_SERVICE_CONFIG")
        lm_config = utils.load_json(self.dream_root / "common" / "generative_configs" / lm_config_file)

        return lm_config

    def dump_lm_config_file(self, lm_config: dict):
        lm_config_file = self.get_environment_value("GENERATIVE_SERVICE_CONFIG")
        utils.dump_json(
            lm_config,
            self.dream_root / "common" / "generative_configs" / lm_config_file,
            overwrite=True,
        )

    def generate_compose(self, drop_ports: bool = True, drop_volumes: bool = True) -> generics.ComposeContainer:
        service_compose = self.service.compose

        if self.environment:
            try:
                service_compose.build.args = self.environment
            except AttributeError:
                service_compose.build = {"args": self.environment}
            service_compose.environment = self.environment

        if drop_ports:
            service_compose.ports = None
        if drop_volumes:
            service_compose.volumes = None

        return service_compose
