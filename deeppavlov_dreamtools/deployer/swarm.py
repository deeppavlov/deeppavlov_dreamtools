import shutil
from pathlib import Path
from typing import Union
import logging

import yaml
from deeppavlov_dreamtools.distconfigs.manager import DreamDist, DreamPipeline, PipelineConfService
from fabric import Connection

# FOR LOCAL TESTS
DREAM_ROOT_PATH_REMOTE = "/home/ubuntu/dream/"
DREAM_ROOT_PATH = Path(__file__).parents[3] / "dream/"

url_http_slice = slice(0, 7)
url_address_slice = slice(7, None)

logging.basicConfig(level=logging.INFO, format="%(asctime)s:%(levelname)s:%(name)s:%(message)s")
logger = logging.getLogger("dreamtools.SwarmDeployer")


class SwarmDeployer:
    # TODO: add getting DREAM_ROOT_PATH from os.env
    # TODO: stdout from terminal to save in log files [later]
    def __init__(self, host: str, path_to_keyfile: str, user_identifier: str, connection: Connection = None):
        """
        self.connection is the fabric.Connection object that allows to run virtual terminal.
        """
        if connection is None:
            self.connection: Connection = Connection(host=host, connect_kwargs={"key_filename": path_to_keyfile})
        else:
            self.connection: Connection = connection
        self.user_identifier = user_identifier

    def deploy(self, dream_dist: DreamDist, dream_root_path_remote: Union[Path, str]) -> None:
        """
        Creates local files and then transfers it to the remote machine (`dream_root_remote`)

        """
        self._set_up_local_configs()

        logger.info(f"Transferring local config objects to remote machine")
        dream_dist_path_remote = Path(dream_root_path_remote) / "assistant_dists" / dream_dist.name
        self.transfer_files_to_remote_machine(
            from_local_path=dream_dist.dist_path, to_remote_path=dream_dist_path_remote
        )
        shutil.rmtree(dream_dist.dist_path)  # delete local files of the created distribution
        logger.info("Building images for distribution")
        self.connection.run(
            self._get_docker_build_command_from_dist_configs(dream_dist, DREAM_ROOT_PATH_REMOTE)
        )
        logger.info("Images built")

        logger.info("Deploying services on the node")
        command = self._get_swarm_deploy_command_from_dreamdist(dream_dist, dream_root_path_remote)
        self.connection.run(command, hide=True)
        logger.info("Services deployed")

        self.connection.run("docker service list")
        self.connection.run("docker node ps")

    def _set_up_local_configs(self):
        prefix = self.user_identifier + "_"
        dream_dist.name = prefix + dream_dist.name

        logger.info(f"Creating files for {dream_dist.name} distribution")

        self.change_pipeline_conf_services_url_for_deployment(dream_pipeline=dream_dist.pipeline_conf, prefix=prefix)
        dream_dist.save(overwrite=True)

        self.create_yml_file_with_explicit_images_in_local_dist(dream_dist=dream_dist)

    def transfer_files_to_remote_machine(self, from_local_path: Union[Path, str], to_remote_path: Union[Path, str]):
        self.connection.run(f"mkdir -p {to_remote_path}")
        for file in Path(from_local_path).iterdir():
            if not file.is_file():
                continue
            self.connection.put(str(file), str(to_remote_path))

    def _get_raw_command_with_filenames(self, dream_dist: DreamDist) -> list[str]:
        """
        Return:
            list with string filenames of the existing configs. List like
            ["docker-compose.override.yml", "dev.yml", "user_deployment.yml"]
        """
        existing_config_filenames = [
            config.DEFAULT_FILE_NAME
            for config in dream_dist.iter_loaded_configs()
            if not isinstance(config, DreamPipeline)
        ]

        deployment_filename = f"{self.user_identifier}_deployment.yml"
        existing_config_filenames.append(deployment_filename)

        return existing_config_filenames

    def _get_docker_build_command_from_dist_configs(self, dream_dist: DreamDist, dream_root_remote_path: str) -> str:
        """
        Returns:
            string like
            `docker-compose -f dream/docker-compose.yml -f dream/assistant_dists/docker-compose.override.yml build`
        """
        config_command_list = []
        dist_path_str = dream_root_remote_path + f"assistant_dists/{dream_dist.name}/"

        existing_configs_filenames = self._get_raw_command_with_filenames(dream_dist)
        for command in existing_configs_filenames:
            if command:
                config_command_list.append("".join(["-f ", dist_path_str, command]))
        config_command_list.insert(0, f"-f {dream_root_remote_path}docker-compose.yml")
        command = " ".join(config_command_list)

        return f"docker-compose {command} build"

    def _get_swarm_deploy_command_from_dreamdist(self, dream_dist: DreamDist, dream_root_remote_path: str) -> str:
        """
        Creates docker-compose up command depending on the loaded configs in the DreamDistribution
        Args:
             dream_dist: DreamDistribution instance
             dream_root_remote_path: REMOTE path to root of dream repository
        Returns:

            string like
            ```
            docker stack deploy -c /home/user/dream/docker-compose.yml
            -c /home/user/dream/assistant_dists/dream/docker-compose.override.yml [and other configs] [dist.name]
            ```
        """
        config_command_list = []
        dist_path_str = dream_root_remote_path + f"assistant_dists/{dream_dist.name}/"

        existing_configs_filenames = self._get_raw_command_with_filenames(dream_dist)
        for command in existing_configs_filenames:
            if command:
                config_command_list.append("".join(["-c ", dist_path_str, command]))

        command = " ".join(config_command_list)

        return f"docker stack deploy {command} {dream_dist.name}"

    @staticmethod
    def change_pipeline_conf_services_url_for_deployment(
        dream_pipeline: DreamPipeline, prefix: str, user_services: list[str] = None
    ) -> None:
        """
        user_services -- the services not to change by this function
        Args:
            dream_pipeline: pipeline object from dream distribution
            user_services: services to be banned from being prefixed
            prefix: prefix to use before address. It is something like `user_`
        """
        for service_group, service_name, service in dream_pipeline.iter_services():
            if user_services is not None and service_name in user_services:
                continue
            try:
                new_url = SwarmDeployer.get_url_prefixed(service, prefix)
            except AttributeError:
                continue
            service.connector.url = new_url

    @staticmethod
    def get_url_prefixed(service: PipelineConfService, prefix: str) -> str:
        """
        pipeline_conf.json
        connector.url with value `http://url:port` -> `http://{prefix}_url:port
        """
        connector_url = service.connector.url
        if connector_url is None:
            raise AttributeError
        return "".join([connector_url[url_http_slice], prefix, connector_url[url_address_slice]])

    def create_yml_file_with_explicit_images_in_local_dist(self, dream_dist: DreamDist) -> None:
        """
        Creates yml file in dream_dist.dist_path directory with name `{user_id}_deployment.yaml` with structure like
        ```
        services:
            agent:
                image: {dream_dist.name}_agent
            asr:
                image: {dream_dist.name}_asr
        ```
        """
        services = {}
        dict_yml = {"version": "3.7", "services": services}
        for yml_config_object in dream_dist.iter_loaded_configs():
            if isinstance(yml_config_object, DreamPipeline):
                continue
            for service_name, _ in yml_config_object.iter_services():
                image_name = f"{dream_dist.name}_{service_name}" if service_name != "mongo" else service_name
                services.update({service_name: {"image": image_name}})
        filepath = dream_dist.dist_path / f"{self.user_identifier}_deployment.yml"
        with open(filepath, "w") as file:
            yaml.dump(dict_yml, file)


if __name__ == "__main__":
    dream_dist = DreamDist.from_name(name="dream", dream_root=DREAM_ROOT_PATH)
    deployer = SwarmDeployer(
        host="ubuntu@aws.com",
        path_to_keyfile="key.pem",
        user_identifier="test",
    )
    deployer.deploy(dream_dist, DREAM_ROOT_PATH_REMOTE)
