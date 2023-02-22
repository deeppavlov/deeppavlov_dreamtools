from pathlib import Path
from typing import Union
from fabric import Connection

from deeppavlov_dreamtools import DreamDist

# FOR LOCAL TESTS
DREAM_ROOT_PATH_REMOTE = "/home/ubuntu/dream/"
DREAM_ROOT_PATH = Path(__file__).parents[3] / "dream/"


class Deployer:
    async def deploy(self, dist: DreamDist, dream_root_remote):
        raise NotImplementedError


class SwarmDeployer(Deployer):
    #TODO: add getting DREAM_ROOT_PATH from os.env
    def __init__(self, host: str, path_to_keyfile: str):
        """
        self.connection is the connection object that allows to run virtual terminal.
        """
        self.connection = Connection(host=host, connect_kwargs={"key_filename": path_to_keyfile})

    def init(self):
        self.connection.run("docker swarm init")

    def deploy(self, dist: DreamDist, dream_root_remote: Union[Path, str]):
        """
        Problems:
            - docker stack deploy doesn't support `build` instruction as it does docker-compose
            - creating environment works bad (can be solved by using workarounds)
        """
        command = self._get_swarm_deploy_command_from_dreamdist(dist, DREAM_ROOT_PATH_REMOTE)
        self.connection.run(command)

    def service_list(self):
        self.connection.run("docker service list")

    def leave(self):
        self.connection.run("docker swarm leave --force")

    @staticmethod
    def _get_swarm_deploy_command_from_dreamdist(dist: DreamDist, dist_path_str: str) -> str:
        """
        Creates docker-compose up command depending on the loaded configs in the DreamDistribution
        Args:
             dist: DreamDistribution instance
             dist_path_str: REMOTE path to root of dream repository
        Returns:
            string like `docker stack deploy -c /home/user/dream/assistant_dists/dream/docker-compose.override.yml
            [and other configs] dream`
        """
        config_command_list = []
        dist_path_str += f"assistant_dists/{dist.name}/"

        compose_override_command = (
            f"-c {dist_path_str + dist.compose_override.DEFAULT_FILE_NAME}" if dist.compose_override else None
        )

        proxy_command = f"-c {dist_path_str + dist.compose_proxy.DEFAULT_FILE_NAME}" if dist.compose_proxy else None

        dev_command = f"-c {dist_path_str + dist.compose_dev.DEFAULT_FILE_NAME}" if dist.compose_dev else None

        config_commands_list = [compose_override_command, proxy_command, dev_command]
        for command in config_commands_list:
            if command:
                config_command_list.append(command)

        command = " ".join(config_commands_list)

        return f"docker stack deploy {command}  {dist.name}"


if __name__ == "__main__":
    dist = DreamDist.from_name(name="dream", dream_root=DREAM_ROOT_PATH)
    deployer = SwarmDeployer(host="ubuntu@ipv4.aws.com", path_to_keyfile="key.pem")
    deployer.deploy(dist, DREAM_ROOT_PATH_REMOTE)
