import logging
import shutil
import subprocess
from pathlib import Path
from typing import List, Union
from urllib.parse import urlparse

import boto3
import docker
import dotenv
import yaml
from pydantic.utils import deep_update

from deeppavlov_dreamtools.deployer.const import DEFAULT_PREFIX, EXTERNAL_NETWORK_NAME
from deeppavlov_dreamtools.deployer.portainer import SwarmClient
from deeppavlov_dreamtools.distconfigs.assistant_dists import (
    AssistantDist,
    DreamComposeDev,
    DreamComposeOverride,
    DreamComposeProxy,
    DreamPipeline,
)

# FOR LOCAL TESTS
DREAM_ROOT_PATH = Path(__file__).resolve().parents[3] / "dream/"

url_http_slice = slice(0, 7)
url_address_slice = slice(7, None)
env_var_name_slice = slice(0, -4)

logging.basicConfig(level=logging.INFO, format="%(asctime)s:%(levelname)s:%(name)s:%(message)s")
logger = logging.getLogger("dreamtools.SwarmDeployer")


class SwarmDeployer:
    # TODO: add getting DREAM_ROOT_PATH from os.env
    # TODO: stdout from terminal to save in log files [later]
    # TODO: deal with versions of images(`cls._create_yml_file_with_explicit_images_in_local_dist`)
    # TODO: write docstring describing flow of configuring config files
    # TODO: issue with name mismatch (spelling-preprocessing sep to underscore)
    # TODO: refactor general logic of choosing prefix (main or stackname)
    # TODO: refactor: implement Single Responsibility principle (Work with Host machine and Remote machine)
    def __init__(
        self,
        user_identifier: str,
        portainer_url: str,
        portainer_key: str,
        registry_addr: str = None,
        user_services: List[str] = None,
        deployment_dict: dict = None
    ):
        """
        Args:
            user_identifier - is used for determination of prefix
            registry_addr   - <registry_url>:<port> if images will be pulling from registry
            deployment_dict: values to update *deployment.yml file.
        """
        self.swarm_client = SwarmClient(portainer_url, portainer_key) if portainer_url else None
        self.user_identifier = user_identifier
        self.registry_addr = registry_addr
        self.user_services = user_services
        self.deployment_dict = deployment_dict

    def deploy(self, dist: AssistantDist) -> None:
        """
        Problem to be solved: deploy dream assistant distributions remotely.
        General steps:
        1) create configuration files on the host machine
        2) build & push images described in those configs from the host machine
        3) on the remote machine pull and deploy services from those images onto the docker stack
        """
        self._set_up_local_configs(dist=dist)
        self.build_and_push_to_registry(dist=dist)

        logger.info("Deploying services on the node")
        self.swarm_client.create_stack(dist.dist_path / f"{self.user_identifier}_deployment.yml", self.user_identifier)
        shutil.rmtree(dist.dist_path)  # delete local files of the created distribution
        logger.info("Services deployed")

    def _set_up_local_configs(self, dist: AssistantDist):
        prefix = self.user_identifier + "_"
        dist.name = prefix + dist.name
        dist.compose_proxy = None

        logger.info(f"Creating files for {dist.name} distribution")

        self._change_pipeline_conf_services_url_for_deployment(dream_pipeline=dist.pipeline_conf, user_prefix=prefix)
        if dist.pipeline_conf.config.connectors:
            self._change_pipeline_conf_connectors_url_for_deployment(dream_pipeline=dist.pipeline_conf, prefix=prefix)
        self._change_waithosts_url(compose_override=dist.compose_override, user_prefix=prefix)
        # TODO: remove env path duplication
        dist.update_env_path(Path("assistant_dists") / dist.name / f"{self.user_identifier}.env")
        dist.del_ports_and_volumes()

        if self.user_services is not None:
            self.user_services.append("agent")
            self._remove_mongo_service_in_dev(dist)
            self._leave_only_user_services(dist)
        dist.save(overwrite=True)

        self._create_dists_env_file(dist, user_prefix=prefix)
        self._create_deployment_yml_file(dist=dist)
        logger.info("Configs been created")
        if self.registry_addr:
            self._login_local()

    def _create_dists_env_file(self, dist: AssistantDist, user_prefix: str):
        """
        cp dream/.env dream/assistant_dists/{dist.name}/{dist.name}.env
        DB_NAME -> stackname (dist.name)
        url that not in self.user_services -> http://prefix_service
        """
        env_dict = dotenv.dotenv_values(dist.dream_root / ".env")
        env_dict["DB_NAME"] = self.user_identifier

        for env_var, env_value in env_dict.items():
            if env_var.endswith("URL"):
                if self.user_services:
                    if urlparse(env_value).hostname in self.user_services:
                        env_dict[env_var] = self.get_url_prefixed(env_value, user_prefix)
                    else:
                        env_dict[env_var] = self.get_url_prefixed(env_value, DEFAULT_PREFIX)
                else:
                    env_dict[env_var] = self.get_url_prefixed(env_value, DEFAULT_PREFIX)

        with open(dist.dist_path / f"{self.user_identifier}.env", "w") as f:
            for var, value in env_dict.items():
                f.write(f"{var}={value}\n")

    def _leave_only_user_services(self, dist: AssistantDist):
        """
        Changes distribution configs - ComposeOverride and ComposeDev - by leaving specified in self.user_service
        """
        filtered_override, filtered_dev = None, None
        for config in dist.iter_loaded_configs():
            if isinstance(config, DreamPipeline):
                continue
            elif isinstance(config, DreamComposeOverride):
                filtered_override = config.filter_services(self.user_services)[1]
            elif isinstance(config, DreamComposeDev):
                filtered_dev = config.filter_services(self.user_services)[1]
        dist.compose_override = filtered_override
        dist.compose_dev = filtered_dev

    def _remove_mongo_service_in_dev(self, dist: AssistantDist):
        if dist.compose_dev and dist.compose_dev.get_service("mongo"):
            dist.compose_dev.remove_service("mongo")

    def _remove_mongo_from_root_docker_compose(self, dream_root_path: Union[Path, str]):
        """
        Removes mongo service from docker-compose file

        Args:
            dream_root_path (Union[Path, str]): The remote path to the root directory of the Dream project.
        """
        dream_root_path = Path(dream_root_path)
        docker_compose_path_remote = dream_root_path / "docker-compose.yml"
        no_mongo_docker_compose_path_remote = dream_root_path / "docker-compose-no-mongo.yml"
        command = (
            f"cp {docker_compose_path_remote} {no_mongo_docker_compose_path_remote} &&"
            f" sed -i '/mongo:/,/^$/d' {no_mongo_docker_compose_path_remote}"
        )

        subprocess.run(command, shell=True)

    def _get_raw_command_with_filenames(self, dist: AssistantDist) -> List[str]:
        """
        Return:
            list with string filenames of the existing configs. List like
            ["docker-compose.override.yml", "dev.yml", "user_deployment.yml"]
        """
        existing_config_filenames = []
        for config in dist.iter_loaded_configs():
            if isinstance(config, (DreamPipeline, DreamComposeProxy)):
                continue
            existing_config_filenames.append(config.DEFAULT_FILE_NAME)

        deployment_filename = f"{self.user_identifier}_deployment.yml"
        existing_config_filenames.append(deployment_filename)

        return existing_config_filenames

    def _get_docker_build_command_from_dist_configs(
        self, dist: AssistantDist, dream_root_remote_path: Union[Path, str]
    ) -> str:
        """
        Returns:
            string like
            `docker-compose -f dream/docker-compose.yml -f dream/assistant_dists/docker-compose.override.yml build`
        """
        config_command_list = [f"-f {dream_root_remote_path / 'docker-compose.yml'}"]

        dist_path_str = dream_root_remote_path / "assistant_dists" / dist.name

        existing_configs_filenames = self._get_raw_command_with_filenames(dist)
        for command in existing_configs_filenames:
            if command:
                config_command_list.append("".join(["-f ", str(dist_path_str / command)]))
        command = " ".join(config_command_list)

        return f"docker compose {command} build"

    def _change_pipeline_conf_services_url_for_deployment(
        self, dream_pipeline: DreamPipeline, user_prefix: str
    ) -> None:
        """
        self.user_services -- the services not to change by this function
        Args:
            dream_pipeline: pipeline object from dream distribution
            self.user_services: services to be banned from being prefixed
            user_prefix: prefix to use before address. It is something like `user_`
        """
        for service_group, service_name, service in dream_pipeline.iter_services():
            pipeline_conf_service_name = urlparse(service.connector.url).hostname
            if self.user_services is not None and pipeline_conf_service_name in self.user_services:
                prefix_ = user_prefix
            else:
                prefix_ = DEFAULT_PREFIX
            try:
                new_url = self.get_url_prefixed(service.connector.url, prefix_)
            except AttributeError:
                continue
            service.connector.url = new_url

    def _change_pipeline_conf_connectors_url_for_deployment(self, dream_pipeline: DreamPipeline, prefix: str):
        for connector_name, connector_object in dream_pipeline.config.connectors.items():
            try:
                url = connector_object.url
                if not url:
                    raise AttributeError
            except AttributeError:
                continue
            service_name = urlparse(url).hostname
            if self.user_services is not None and service_name in self.user_services:
                prefix_ = prefix
            else:
                prefix_ = DEFAULT_PREFIX
            connector_object.url = SwarmDeployer.get_url_prefixed(connector_object.url, prefix_)

    def _change_waithosts_url(self, compose_override: DreamComposeOverride, user_prefix: str):
        wait_hosts = compose_override.config.services["agent"].environment["WAIT_HOSTS"].split(", ")
        for i in range(len(wait_hosts)):
            service_name = wait_hosts[i].split(":")[0]
            if self.user_services and service_name in self.user_services:
                wait_hosts[i] = "".join([user_prefix, wait_hosts[i]])
            else:
                wait_hosts[i] = "".join([DEFAULT_PREFIX, wait_hosts[i]])
        compose_override.config.services["agent"].environment["WAIT_HOSTS"] = ", ".join(wait_hosts)

    @staticmethod
    def get_url_prefixed(url: str, prefix: str) -> str:
        """
        pipeline_conf.json
        connector.url with value `http://url:port` -> `http://{prefix}_url:port
        """
        if not url:
            raise AttributeError
        return "".join([url[url_http_slice], prefix, url[url_address_slice]])

    def _create_deployment_yml_file(self, dist: AssistantDist) -> None:
        """
        Creates yml file in dist.dist_path directory with name `{user_id}_deployment.yaml` with structure like
        ```
        services:
            agent:
                image: {dist.name}_agent
            asr:
                image: {dist.name}_asr
        ```
        """
        deployment_dict = self._create_deployment_dict(dist)
        self._save_deployment_dict_in_dist_path(deployment_dict, dist.dist_path)
        self._configure_deployment_file(dist)

    def _create_services_dict(self, dist: AssistantDist) -> dict:
        """
        Creates description of the services to be dumped in *_deployment.yml.
        Description based on distribution object
        """
        services = {}

        for yml_config_object in dist.iter_loaded_configs():
            if isinstance(yml_config_object, DreamPipeline):
                continue
            for service_name, _ in yml_config_object.iter_services():
                image_name = f"{dist.name}_{service_name}" if service_name != "mongo" else service_name
                if self.registry_addr:
                    services.update({service_name: {"image": f"{self.registry_addr}/{image_name}"}})
                else:
                    services.update({service_name: {"image": image_name}})
        services = deep_update(
            services,
            {
                "agent": {
                    "command": f"sh -c 'bin/wait && python -m deeppavlov_agent.run agent.pipeline_config=assistant_dists/{dist.dist_path.name}/pipeline_conf.json'",
                    "env_file": f"assistant_dists/{dist.name}/{self.user_identifier}.env",
                }
            },
        )
        return services

    def _create_deployment_dict(self, dist: AssistantDist) -> dict:
        """
        Creates a python dict representing *_deployment.yml file
        Deployment describes network, services and version
        """
        networks = {"networks": {"default": {"external": True, "name": EXTERNAL_NETWORK_NAME}}}

        services = self._create_services_dict(dist)
        dict_yml = {"version": "3.7", "services": services, **networks}
        if self.deployment_dict is not None:
            dict_yml = deep_update(dict_yml, self.deployment_dict)
        return dict_yml

    def _save_deployment_dict_in_dist_path(self, dict_yml: dict, dist_path: Path) -> None:
        deployer_filepath = dist_path / f"{self.user_identifier}_deployment.yml"
        with open(deployer_filepath, "w") as file:
            yaml.dump(dict_yml, file)

    def _configure_deployment_file(self, dist: AssistantDist) -> None:
        """
        Creates final deployment file based on config compose files of an assistant distribution
        """
        configs_list = self._get_existing_configs_list(dist)

        deployment_file_path: Path = configs_list[-1]
        temporary_deployment_file_path: str = str(deployment_file_path)[:-1]

        if not deployment_file_path.name.endswith("_deployment.yml"):
            raise ValueError(f"Expected *deployment.yml to be the last file.")
        cmd = " ".join(f"-f {config}" for config in configs_list)
        subprocess.run(
            f"docker compose {cmd} config  > {temporary_deployment_file_path} && mv {temporary_deployment_file_path} "
            f"{deployment_file_path}",
            shell=True,
        )
        subprocess.run(
            f'sed -i "/published:/s/\\"//g" {deployment_file_path} && echo "version: \'3.7\'" >> '
            f'{deployment_file_path} && sed -i "/^name:/d" {deployment_file_path}',
            shell=True,
        )

    def _get_existing_configs_list(self, dist: AssistantDist) -> List[Path]:
        """
        Returns:
            list like [
            PosixPath('.../dream/docker-compose-no-mongo.yml'),
            PosixPath('.../dream/assistant_dists/deepy_faq/docker-compose.override.yml'),
            PosixPath('.../dream/assistant_dists/deepy_faq/test_deployment.yml')
            ]
        """
        if not self.user_services:
            docker_compose_pathfile = dist.dream_root / "docker-compose.yml"
        else:
            docker_compose_pathfile = dist.dream_root / "docker-compose-no-mongo.yml"
        configs_list = [
            docker_compose_pathfile,
        ]

        existing_configs_filenames = self._get_raw_command_with_filenames(dist)
        for command in existing_configs_filenames:
            if command:
                configs_list.append(dist.dist_path / command)

        return configs_list

    def remove_services(self, stack_name: str):
        self.swarm_client.delete_stack(stack_name)
        logger.info(f"{stack_name} successfully removed")

    def push_images(self, image_names: List[str]):
        """
        HOST MACHINE
        repository_name == stack_name == self.user_identifier
        docker login must be configured
        """
        ecr_client = boto3.client("ecr")
        docker_client = docker.from_env()

        for image_name in image_names:
            image_name_ = image_name
            if ":" in image_name:
                image_name_, tag = image_name.split(":")

            if self._check_if_repository_exists(ecr_client=ecr_client, repository_name=image_name_):
                response = ecr_client.describe_repositories(
                    repositoryNames=[
                        image_name_,
                    ]
                )
                repository_description = response["repositories"][0]
            else:
                repository_description = ecr_client.create_repository(repositoryName=image_name_)["repository"]
            repository_uri = repository_description["repositoryUri"]

            # image = docker_client.images.get(image_name)
            # image.tag(repository_uri, "test")
            # image.tags doesn't guarantee that tags in python objects  match with docker tags in system, so then
            # composing string is required
            image_tag = f"{repository_uri}:{self.user_identifier}"

            try:
                logger.info(f"Pushing image {image_name_}")
                print(docker_client.images.push(repository_uri))
            except docker.errors.APIError as e:
                logger.error(f"While pushing image raised error: {e}")

    def _check_if_repository_exists(self, ecr_client, repository_name):
        try:
            ecr_client.describe_repositories(
                repositoryNames=[
                    repository_name,
                ]
            )
            return True

        except ecr_client.exceptions.RepositoryNotFoundException as e:
            logger.info(f"{repository_name} repository wasn't found. It will be created")
            return False

    def _build_image_on_local(self, dist: AssistantDist):
        logger.info("Building images on local machine")
        process = subprocess.Popen(
            self._get_docker_build_command_from_dist_configs(dist, dist.dream_root),
            cwd=dist.dream_root,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        output, error = process.communicate()
        if process.returncode != 0:
            raise ChildProcessError(f"Failed to build images: {error.decode()}.")
        logger.info("Images built")

    def _get_image_names_of_the_dist(self, dist: AssistantDist):
        if self.user_services:
            image_names = ["".join([dist.name, "_", user_service]) for user_service in self.user_services]
        else:
            image_names = [
                "".join([dist.name, "_", service_name]) for service_name, _ in dist.compose_override.iter_services()
            ]
        return image_names

    def build_and_push_to_registry(self, dist: AssistantDist):
        """
        HOST MACHINE
        """
        if self.user_services or True:
            self._remove_mongo_from_root_docker_compose(dist.dream_root)
        self._build_image_on_local(dist)
        image_names: List[str] = self._get_image_names_of_the_dist(dist)
        self.push_images(image_names)

    def _login_local(self):
        subprocess.run(
            f"aws ecr get-login-password --region us-east-1|"
            f"docker login --username AWS --password-stdin {self.registry_addr}",
            shell=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.STDOUT,
        )


if __name__ == "__main__":
    dream_dist = AssistantDist.from_name(name="deepy_faq", dream_root=DREAM_ROOT_PATH)
    deployer = SwarmDeployer(
        user_identifier="test",
        user_services=["faq-skill"],
        portainer_key=None,
        portainer_url=None,
    )
    deployer.deploy(dream_dist)  # mutates python object(dist.name->user_identifier_name)
