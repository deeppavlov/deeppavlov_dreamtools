import json
import logging
import shutil
from pathlib import Path
from typing import List, Union

import dotenv
import yaml
from deeppavlov_dreamtools.distconfigs.assistant_dists import (
    AssistantDist,
    DreamComposeDev,
    DreamComposeOverride,
    DreamPipeline,
    DreamComposeProxy,
)
from fabric import Connection

from const import DEFAULT_PREFIX, EXTERNAL_NETWORK_NAME

# FOR LOCAL TESTS
DREAM_ROOT_PATH_REMOTE = Path("/home/ubuntu/dream/")
DREAM_ROOT_PATH = Path(__file__).resolve().parents[3] / "dream/"

url_http_slice = slice(0, 7)
url_address_slice = slice(7, None)
env_var_name_slice = slice(0, -4)

logging.basicConfig(level=logging.INFO, format="%(asctime)s:%(levelname)s:%(name)s:%(message)s")
logger = logging.getLogger("dreamtools.SwarmDeployer")


class SwarmDeployer:
    # TODO: add getting DREAM_ROOT_PATH from os.env
    # TODO: stdout from terminal to save in log files [later]
    # TODO: add support of multiple nodes (`cls.check_for_errors_in_services`)
    # TODO: parse `cls.check_for_errors_in_services` using `--format json` and python objects?
    # TODO: deal with the versions of images(`cls._create_yml_file_with_explicit_images_in_local_dist`)
    # TODO: write docstring describing flow of configuring config files
    def __init__(
        self,
        host: str,
        path_to_keyfile: str,
        user_identifier: str,
        registry_addr: str = None,
        user_services: List[str] = None,
        **kwargs,
    ):
        """
        Args:
            self.connection - the fabric.Connection object that allows to run virtual terminal.
            user_identifier - is used for determination of prefix
            registry_addr   - <registry_url>:<port> if images will be pulling from registry
        """
        self.connection: Connection = Connection(host=host, connect_kwargs={"key_filename": path_to_keyfile}, **kwargs)
        self.user_identifier = user_identifier
        self.registry_addr = registry_addr
        self.user_services = user_services

    def deploy(self, dist: AssistantDist, dream_root_path_remote: Union[Path, str]) -> None:
        """
        Creates local files and then transfers it to the remote machine (`dream_root_remote`)

        """
        self._set_up_local_configs(dist=dist)
        self._transfer_configs_to_remote_machine(dist, dream_root_path_remote)
        shutil.rmtree(dist.dist_path)  # delete local files of the created distribution
        self._build_images(dist, dream_root_path_remote)

        logger.info("Deploying services on the node")
        self.connection.run(self._get_swarm_deploy_command_from_dreamdist(dist, dream_root_path_remote), hide=True)
        logger.info("Services deployed")

        self._check_for_errors_in_node_ps()  # DOESN'T SUPPORT MULTIPLE NODES. Status will be displayed in logs
        self._check_for_errors_in_all_services()

    def _set_up_local_configs(self, dist: AssistantDist):
        prefix = self.user_identifier + "_"
        dist.name = prefix + dist.name
        dist.compose_proxy = None

        logger.info(f"Creating files for {dist.name} distribution")

        self._change_pipeline_conf_services_url_for_deployment(dream_pipeline=dist.pipeline_conf, prefix=prefix)
        if dist.pipeline_conf.config.connectors:
            self._change_pipeline_conf_connectors_url_for_deployment(
                dream_pipeline=dist.pipeline_conf, prefix=DEFAULT_PREFIX
            )

        if self.user_services is not None:
            self.user_services.append("agent")
            self._remove_mongo_services_if_any(dist, DREAM_ROOT_PATH_REMOTE)
            self._leave_only_user_services(dist)
        dist.save(overwrite=True)

        self._create_dists_env_file(dist)
        self._create_yml_file_with_explicit_images_in_local_dist(dist=dist)

    def _create_dists_env_file(self, dist: AssistantDist):
        """
        cp dream/.env dream/assistant_dists/{dist.name}/{dist.name}.env
        DB_NAME -> stackname (dist.name)
        url that not in self.user_services -> http://prefix_service
        """
        env_dict = dotenv.dotenv_values(dist.dream_root / ".env")
        env_dict["DB_NAME"] = self.user_identifier

        for env_var, env_value in env_dict.items():
            if (
                self.user_services
                and env_var.endswith("URL")
                and env_var[env_var_name_slice].lower() not in self.user_services
            ):
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

    def _remove_mongo_services_if_any(self, dist: AssistantDist, dream_root_path_remote: Union[Path, str]):
        """
        Removes mongo service from docker-compose file and from python object of dev.yml

        Args:
            dist (AssistantDist): The distribution object to modify.
            dream_root_path_remote (Union[Path, str]): The remote path to the root directory of the Dream project.
        """
        dream_root_path_remote = Path(dream_root_path_remote)
        docker_compose_path_remote = dream_root_path_remote / "docker-compose.yml"
        no_mongo_docker_compose_path_remote = dream_root_path_remote / "docker-compose-no-mongo.yml"

        if dist.compose_dev.get_service("mongo"):
            dist.compose_dev.remove_service("mongo")

        self.connection.run(
            f"cp {docker_compose_path_remote} {no_mongo_docker_compose_path_remote} &&"
            f"sed -i '/mongo:/,/^$/d' {no_mongo_docker_compose_path_remote}"
        )

    def _transfer_configs_to_remote_machine(self, dist: AssistantDist, dream_root_path_remote: str):
        logger.info(f"Transferring local config objects to remote machine")

        dist_path_remote = Path(dream_root_path_remote) / "assistant_dists" / dist.name
        self.connection.run(f"mkdir -p {dist_path_remote}")
        for file in Path(dist.dist_path).iterdir():
            if not file.is_file():
                continue
            self.connection.put(str(file), str(dist_path_remote))

    def _build_images(self, dist: AssistantDist, dream_root_path_remote: str):
        logger.info("Building images for distribution")
        with self.connection.cd(dream_root_path_remote):
            self.connection.run(
                self._get_docker_build_command_from_dist_configs(dist, dream_root_path_remote), hide=True
            )
        logger.info("Images built")

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

    def _get_docker_build_command_from_dist_configs(self, dist: AssistantDist, dream_root_remote_path: Union[Path, str]) -> str:
        """
        Returns:
            string like
            `docker-compose -f dream/docker-compose.yml -f dream/assistant_dists/docker-compose.override.yml build`
        """
        if not self.user_services:
            docker_compose_command = "-f docker-compose.yml"
        else:
            docker_compose_command = "-f docker-compose-no-mongo.yml"

        config_command_list = [docker_compose_command, ]

        dist_path_str = dream_root_remote_path / "assistant_dists" / dist.name

        existing_configs_filenames = self._get_raw_command_with_filenames(dist)
        for command in existing_configs_filenames:
            if command:
                config_command_list.append("".join(["-f ", str(dist_path_str / command)]))
        command = " ".join(config_command_list)

        return f"docker compose {command} build"

    def _get_swarm_deploy_command_from_dreamdist(self, dist: AssistantDist, dream_root_remote_path: Union[Path, str]) -> str:
        """
        Creates docker-compose up command depending on the loaded configs in the AssistantDistribution
        Args:
             dist: AssistantDistribution instance
             dream_root_remote_path: REMOTE path to root of dream repository
        Returns:

            string like
            ```
            docker stack deploy -c /home/user/dream/docker-compose.yml
            -c /home/user/dream/assistant_dists/dream/docker-compose.override.yml [and other configs] [dist.name]
            ```
        """
        config_command_list = []

        dist_path = Path(dream_root_remote_path) / "assistant_dists" / dist.name
        if not self.user_services:
            docker_compose_pathfile = dream_root_remote_path / "docker-compose.yml"
        else:
            docker_compose_pathfile = dream_root_remote_path / "docker-compose-no-mongo.yml"
        config_command_list.append(f"-c {docker_compose_pathfile}")

        existing_configs_filenames = self._get_raw_command_with_filenames(dist)
        for command in existing_configs_filenames:
            if command:
                config_command_list.append("".join(["-c ", str(dist_path / command)]))

        command = " ".join(config_command_list)

        return f"docker stack deploy {command} {dist.name}"

    def _change_pipeline_conf_services_url_for_deployment(self, dream_pipeline: DreamPipeline, prefix: str) -> None:
        """
        self.user_services -- the services not to change by this function
        Args:
            dream_pipeline: pipeline object from dream distribution
            self.user_services: services to be banned from being prefixed
            prefix: prefix to use before address. It is something like `user_`
        """
        for service_group, service_name, service in dream_pipeline.iter_services():
            if self.user_services is not None and service_name in self.user_services:
                prefix_ = self.user_identifier
            else:
                prefix_ = prefix
            try:
                new_url = self.get_url_prefixed(service.connector.url, prefix_)
            except AttributeError:
                continue
            service.connector.url = new_url

    @staticmethod
    def _change_pipeline_conf_connectors_url_for_deployment(dream_pipeline: DreamPipeline, prefix: str):
        for connector_name, connector_object in dream_pipeline.config.connectors.items():
            try:
                url = connector_object.url
                if not url:
                    raise AttributeError
            except AttributeError:
                continue
            connector_object.url = SwarmDeployer.get_url_prefixed(connector_object.url, prefix)

    @staticmethod
    def get_url_prefixed(url: str, prefix: str) -> str:
        """
        pipeline_conf.json
        connector.url with value `http://url:port` -> `http://{prefix}_url:port
        """
        if not url:
            raise AttributeError
        return "".join([url[url_http_slice], prefix, url[url_address_slice]])

    def _create_yml_file_with_explicit_images_in_local_dist(self, dist: AssistantDist) -> None:
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
        services = {}
        networks = {"networks": {"default": {"external": True, "name": EXTERNAL_NETWORK_NAME}}}
        dict_yml = {"version": "3.7", "services": services, **networks}

        for yml_config_object in dist.iter_loaded_configs():
            if isinstance(yml_config_object, DreamPipeline):
                continue
            for service_name, _ in yml_config_object.iter_services():
                image_name = f"{dist.name}_{service_name}" if service_name != "mongo" else service_name
                if self.registry_addr:
                    services.update({service_name: {"image": f"{self.registry_addr}/{service_name}"}})
                else:
                    services.update({service_name: {"image": image_name}})

        filepath = dist.dist_path / f"{self.user_identifier}_deployment.yml"
        with open(filepath, "w") as file:
            yaml.dump(dict_yml, file)

    def _check_for_errors_in_node_ps(self):
        """
        docker node ps - get running tasks on master node
        awk parameters explained:
            -F '   +' : sets the field separator to a regular expression consisting of three or more consecutive spaces.
            -v OFS=';' : sets the output field separator to a semicolon (space isn't suitable in this case)
            'NR>1 && $7 != "" {print $1, $2, $4, $7}' -- excluding header, shows id, name, node, error if an error occurs
            $1, $2, $4, $7 - data in columns ID, NAME, NODE, ERROR
        """
        result = self.connection.run(
            "docker node ps | awk -F '   +' -v OFS=';' 'NR>1 && $7 != \"\" {print $1, $2, $4, $7}'", hide=True
        )
        if not result.stdout:
            logger.info(f"No errors found using `docker node ps`")
        for docker_service in result.stdout.splitlines():
            ID, NAME, NODE, ERROR_DESCRIPTION = docker_service.split(";")
            logger.error(f"The service couldn't be deployed: {ID=}, {NAME=}, {NODE=}, {ERROR_DESCRIPTION=}")

    def _check_for_errors_in_all_services(self):
        """
        docker service ls --format json -- shows information about all services in stack. In case of `Replicas` of
        services has value 0/n method sends log with service information
        """
        undeployed_services_id_list: list[str] = []
        result = self.connection.run("docker service ls --format json", hide=True)
        for service_str in result.stdout.splitlines():
            service = json.loads(service_str)
            if service["Replicas"].startswith("0"):
                undeployed_services_id_list.append(service["ID"])

        undeployed_services_id_str = " ".join(undeployed_services_id_list)
        command_get_service_state = " ".join(
            ["docker service ps", undeployed_services_id_str, "--no-trunc --format json"]
        )
        result = self.connection.run(command_get_service_state, hide=True)
        for service_str in result.stdout.splitlines():
            service = json.loads(service_str)
            if service.get("Error"):
                logger.error(f"Error raised in service: {service}")

    def remove_services(self, stack_name: str):
        self.connection.run(f"docker stack rm {stack_name}")
        logger.info(f"{stack_name} successfully removed")


if __name__ == "__main__":
    dream_dist = AssistantDist.from_name(name="dream", dream_root=DREAM_ROOT_PATH)
    deployer = SwarmDeployer(
        host="ubuntu@aws.com",
        path_to_keyfile="key.pem",
        user_identifier="test",
    )
    deployer.deploy(dream_dist, DREAM_ROOT_PATH_REMOTE)  # mutates python object(dist.name->user_identifier_name)
