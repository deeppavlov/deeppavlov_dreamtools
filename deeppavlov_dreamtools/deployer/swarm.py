import logging
import shutil
import subprocess
from pathlib import Path
from typing import List
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
    DreamComposeOverride,
    DreamPipeline,
)

# FOR LOCAL TESTS
DREAM_ROOT_PATH = Path(__file__).resolve().parents[3] / "dream/"

url_http_slice = slice(0, 7)
url_address_slice = slice(7, None)
env_var_name_slice = slice(0, -4)

logging.basicConfig(level=logging.INFO, format="%(asctime)s:%(levelname)s:%(name)s:%(message)s")
logger = logging.getLogger("dreamtools.SwarmDeployer")


class DeployerState:
    CREATING_CONFIG_FILES = "CREATING_CONFIG_FILES"
    BUILDING_IMAGE = "BUILDING_IMAGE"
    PUSHING_IMAGES = "PUSHING_IMAGES"
    DEPLOYING_STACK = "DEPLOYING_STACK"
    DEPLOYED = "DEPLOYED"


class CloudServiceName:
    AMAZON = "amazon"
    LOCAL = "local"


class DeployerError:
    def __init__(self, state: str, exc: Exception, message: str = None):
        self.state = state
        self._exc = exc
        self.exception = f"{type(exc).__name__}"
        self.message = message or str(exc)

    def dict(self):
        return {"state": self.state, "exception": self.exception, "message": self.message}


class SwarmDeployer:
    # TODO: add getting DREAM_ROOT_PATH from os.env
    # TODO: stdout from terminal to save in log files [later]
    # TODO: deal with versions of images(`cls._create_yml_file_with_explicit_images_in_local_dist`)
    # TODO: write docstring describing flow of configuring config files
    # TODO: issue with name mismatch (spelling-preprocessing sep to underscore)
    # TODO: refactor general logic of choosing prefix (main or stackname)
    # TODO: refactor: implement Single Responsibility principle (Work with Host machine and Remote machine)
    # TODO: add check that stack already doesn't exist. Add free resources check
    def __init__(
        self,
        user_identifier: str,
        portainer_url: str,
        portainer_key: str,
        registry_addr: str = None,
        user_services: List[str] = None,
        deployment_dict: dict = None,
        default_prefix: str = DEFAULT_PREFIX,
        cloud_service_name: str = CloudServiceName.AMAZON
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
        self.default_prefix = default_prefix
        self.cloud_service_name = cloud_service_name

    def deploy(self, dist: AssistantDist):
        """
        Problem to be solved: deploy dream assistant distributions remotely.
        General steps:
        1) create configuration files on the host machine
        2) build & push images described in those configs from the host machine
        3) on the remote machine pull and deploy services from those images onto the docker stack

        Yields:
            tuple of (state, updates, error) events from the deployment process
        """
        state = DeployerState.CREATING_CONFIG_FILES
        try:
            yield state, {}, None
            self._set_up_user_dist(dist=dist)

            # self.build_and_push_to_registry(dist=dist)
            state = DeployerState.BUILDING_IMAGE
            yield state, {}, None
            self._build_image_on_local(dist=dist)

            state = DeployerState.PUSHING_IMAGES
            yield state, {}, None
            self.push_images(dist=dist)

            # logger.info("Deploying services on the node")
            state = DeployerState.DEPLOYING_STACK
            yield state, {}, None
            stack = self.swarm_client.create_stack(self._get_deployment_path(dist), self.user_identifier)
            shutil.rmtree(dist.dist_path)  # delete local files of the created distribution
        except Exception as e:
            yield None, {}, DeployerError(state, e)
            raise e

        yield DeployerState.DEPLOYED, {"stack_id": stack.Id}, None
        # logger.info("Services deployed")

    def _set_up_user_dist(self, dist: AssistantDist):
        prefix = self.user_identifier + "_"
        new_name = prefix + dist.name
        try:
            dist.name = new_name
        except FileExistsError:
            shutil.rmtree(dist.dist_path.with_name(new_name))
            dist.name = new_name
        dist.compose_dev, dist.compose_proxy, dist.compose_local = None, None, None

        logger.info(f"Creating files for {dist.name} distribution")

        self._change_pipeline_conf_services_url_for_deployment(dream_pipeline=dist.pipeline_conf, user_prefix=prefix)
        if dist.pipeline_conf.config.connectors:
            self._change_pipeline_conf_connectors_url_for_deployment(dream_pipeline=dist.pipeline_conf, prefix=prefix)
        self._change_waithosts_url(compose_override=dist.compose_override, user_prefix=prefix)
        # TODO: remove env path duplication
        services = dist.compose_override.config.services
        for service_name in services:
            if services[service_name].env_file is not None:
                services[service_name].env_file = dist.dist_path / ".env"
        dist.del_ports_and_volumes()

        if self.user_services is not None:
            self.user_services.append("agent")
            dist.compose_override = dist.compose_override.filter_services(self.user_services)[1]
        dist.save(overwrite=True, generate_configs=False)

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
        logger.info("DREAM .ENV FILE \n", env_dict)
        env_dict["DB_NAME"] = self.user_identifier.split('_')[-1]

        for env_var, env_value in env_dict.items():
            if env_var.endswith("URL"):
                if self.user_services:
                    if urlparse(env_value).hostname in self.user_services:
                        env_dict[env_var] = self.get_url_prefixed(env_value, user_prefix)
                    else:
                        env_dict[env_var] = self.get_url_prefixed(env_value, self.default_prefix)
                else:
                    env_dict[env_var] = self.get_url_prefixed(env_value, self.default_prefix)
        try:
            with open(dist.dist_path / ".env", "w") as f:
                for var, value in env_dict.items():
                    f.write(f"{var}={value}\n")
        except IOError as e:
            logger.info(f"Error writing to {dist.dist_path}/.env : {e}")

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
                prefix_ = self.default_prefix
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
                prefix_ = self.default_prefix
            connector_object.url = SwarmDeployer.get_url_prefixed(connector_object.url, prefix_)

    def _change_waithosts_url(self, compose_override: DreamComposeOverride, user_prefix: str):
        wait_hosts = compose_override.config.services["agent"].environment["WAIT_HOSTS"]
        if not wait_hosts:
            logger.warning('WAIT_HOSTS is empty')
            return
        wait_hosts = wait_hosts.split(", ")
        for i in range(len(wait_hosts)):
            service_name = wait_hosts[i].split(":")[0]
            if self.user_services and service_name in self.user_services:
                wait_hosts[i] = "".join([user_prefix, wait_hosts[i]])
            else:
                wait_hosts[i] = "".join([self.default_prefix, wait_hosts[i]])
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
        self._save_deployment_dict_in_dist_path(deployment_dict, dist)
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
                if service_name.endswith('-prompted-skill'):
                    image_name = f'prompted-skill:{dist.name}_{service_name.replace("-prompted-skill", "")}'
                else:
                    image_name = f"{service_name}:{dist.name}" if service_name != "mongo" else service_name
                if self.registry_addr:
                    services.update({service_name: {"image": f"{self.registry_addr}/{image_name}"}})
                else:
                    services.update({service_name: {"image": image_name}})
        services = deep_update(
            services,
            {
                "agent": {
                    "command": f"sh -c 'bin/wait && python -m deeppavlov_agent.run agent.pipeline_config=assistant_dists/{dist.dist_path.name}/pipeline_conf.json'",
                    "env_file": f"assistant_dists/{dist.name}/.env",
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

    # TODO: consider moving deployment_path to AssistantDist as property
    def _get_deployment_path(self, dist: AssistantDist) -> Path:
        return dist.dist_path / "deployment.yml"

    def _save_deployment_dict_in_dist_path(self, dict_yml: dict, dist: AssistantDist) -> None:
        deployer_filepath = self._get_deployment_path(dist)
        with open(deployer_filepath, "w") as file:
            yaml.dump(dict_yml, file)

    def _configure_deployment_file(self, dist: AssistantDist) -> None:
        """
        Creates final deployment file based on config compose files of an assistant distribution
        """
        docker_compose_pathfile = dist.dream_root / "docker-compose.yml"
        override_path = dist.dist_path / dist.compose_override.DEFAULT_FILE_NAME
        deployment_file_path = self._get_deployment_path(dist)
        temporary_deployment_file_path = str(deployment_file_path)[:-1]
        cmd = " ".join(f"-f {config}" for config in (docker_compose_pathfile, override_path, deployment_file_path))

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
        if self.user_services:  # remove mongo
            with open(deployment_file_path) as fin:
                data = yaml.safe_load(fin)
                data['services'].pop('mongo', None)
            with open(deployment_file_path, 'w') as fout:
                yaml.dump(data, fout)

    def remove_services(self, stack_name: str):
        self.swarm_client.delete_stack(stack_name)
        logger.info(f"{stack_name} successfully removed")

    def push_images(self, dist):
        """
        HOST MACHINE
        repository_name == stack_name == self.user_identifier
        docker login must be configured
        """
        is_amazon_registry = self.cloud_service_name == CloudServiceName.AMAZON

        with open(self._get_deployment_path(dist)) as fin:
            deployment = yaml.safe_load(fin.read())
        for service_name, service in deployment['services'].items():
            try:
                image_name_ = image_name = service['image']
            except KeyError:
                raise KeyError(f'there is no "image" key in {service_name}')
            # TODO: replace with regex
            if ":" in image_name:
                *image_name_, tag = image_name.split(":")
                image_name_ = ":".join(image_name_)
            if "/" in image_name_:
                _, image_name_ = image_name_.split("/")

            if is_amazon_registry:
                ecr_client = boto3.client("ecr")
                self._log_or_create_aws_repository(ecr_client, image_name_)

            # image = docker_client.images.get(image_name)
            # image.tag(repository_uri, "test")
            # image.tags doesn't guarantee that tags in python objects  match with docker tags in system, so then
            # composing string is required
        try:
            push_cmd = f'docker compose -f {self._get_deployment_path(dist)} --project-directory {dist.dream_root} push'
            logger.info("Pushing images")
            process = subprocess.Popen(
                push_cmd,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            output, error = process.communicate()
            if process.returncode != 0:
                raise ChildProcessError(f"Failed to push images: {error.decode()}.")
            logger.info(f"Images pushed")
        except docker.errors.APIError as e:
            logger.error(f"While pushing image raised error: {e}")

    def _log_or_create_aws_repository(self, ecr_client, image_name_: str) -> None:
        if self._check_if_repository_exists(ecr_client=ecr_client, repository_name=image_name_):
            response = ecr_client.describe_repositories(
                repositoryNames=[
                    image_name_,
                ]
            )
            repository_description = response["repositories"][0]
            logger.info(f'initialized {repository_description["repositoryUri"]} repository')
        else:
            repository_description = ecr_client.create_repository(repositoryName=image_name_)["repository"]
            logger.info(f'{repository_description["repositoryUri"]} found')

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
        except Exception as e:
            raise ValueError(f'Got {repr(e)} error for {repository_name}')

    def _build_image_on_local(self, dist: AssistantDist):
        build_cmd = f'docker compose -f {self._get_deployment_path(dist)} --project-directory {dist.dream_root} build'
        logger.info("Building images on local machine")
        process = subprocess.Popen(
            build_cmd,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        output, error = process.communicate()
        if process.returncode != 0:
            raise ChildProcessError(f"Failed to build images: {error.decode()}.")
        logger.info("Images built")

    def build_and_push_to_registry(self, dist: AssistantDist):
        """
        HOST MACHINE
        """
        self._build_image_on_local(dist)
        self.push_images(dist)

    def _login_local(self):
        subprocess.run(
            f"aws ecr get-login-password --region us-east-1|"
            f"docker login --username AWS --password-stdin {self.registry_addr}",
            shell=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.STDOUT,
        )
        # TODO: check awscli version, to choose login type, verify login success
        subprocess.run(
            f"eval $(aws ecr get-login --no-include-email)",
            shell=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.STDOUT,
        )


if __name__ == "__main__":
    dream_dist = AssistantDist.from_name(name='string_de0dab80', dream_root=DREAM_ROOT_PATH)

    def get_services(dist: AssistantDist):
        services = dist.compose_override.config.services.keys()
        user_services = [service for service in services if service.endswith('-prompted-skill')]
        user_services.append('agent')
        if 'prompt-selector' in services:
            user_services.append('prompt-selector')
        return user_services
    deployer = SwarmDeployer(
        user_identifier=dream_dist.name,
        user_services=get_services(dream_dist),
        portainer_key=None,
        portainer_url=None,
    )
    deployer._set_up_user_dist(dream_dist)
    # deployer.deploy(dream_dist)  # mutates python object(dist.name->user_identifier_name)
