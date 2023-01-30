from deeppavlov_dreamtools import DreamDist


class Deployer:
    def __init__(self):
        """"""

    def deploy(self, dist: DreamDist):
        """"""


class SwarmDeployer(Deployer):
    def __init__(self, connector):
        """"""
        self.docker = DockerSwarm(...)

    def deploy(self, dist: DreamDist):
        """"""
        ...
        self.docker.deploy(...)


deployer = SwarmDeployer(...)
deployer.deploy()
