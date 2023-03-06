from pathlib import Path

import pytest

from deeppavlov_dreamtools.tests.fixtures import list_of_dream_dist, dream_root_dir
from deeppavlov_dreamtools.distconfigs.manager import DreamDist, PipelineConfService
from deeppavlov_dreamtools.deployer.swarm import SwarmDeployer


@pytest.fixture
def swarm_deployer_instance():
    swarm_deployer = SwarmDeployer(host="0", path_to_keyfile="0", connection=1, user_identifier="test")
    yield swarm_deployer


def test_get_url_prefixed(dream_root_dir):
    service: PipelineConfService = DreamDist.from_name(
        name="dream", dream_root=dream_root_dir
    ).pipeline_conf.config.services.annotators["spelling_preprocessing"]
    SwarmDeployer.get_url_prefixed(service, "test_")
    assert service.connector.url == "http://test_spelling-preprocessing:8074/respond"


def test_change_pipeline_conf_services_url_for_deployment(list_of_dream_dist: list[DreamDist]):
    for dream_dist in list_of_dream_dist:
        SwarmDeployer.change_pipeline_conf_services_url_for_deployment(dream_dist.pipeline_conf, "test_")
        for _, service_name, service in dream_dist.pipeline_conf.iter_services():
            try:
                url = service.connector.url
            except AttributeError:
                continue
            if url is None or service_name == "mongo":
                continue

            assert url.startswith("http://test_")


def test_create_yml_file_with_explicit_images_in_local_dist(dream_root_dir, swarm_deployer_instance):
    dream_dist = DreamDist.from_name(dream_root=dream_root_dir, name="dream")
    swarm_deployer_instance.create_yml_file_with_explicit_images_in_local_dist(dream_dist)
    dream_dist_path = dream_dist.dist_path
    filepath = dream_dist_path / "test_deployment.yml"
    assert filepath.exists()
    # check if file isn't empty
    assert filepath.stat().st_size > 0


def test_swarmdeployer_commands(dream_root_dir, swarm_deployer_instance):
    dream_dist = DreamDist.from_name(dream_root=dream_root_dir, name="dream")
    command = swarm_deployer_instance._get_swarm_deploy_command_from_dreamdist(dream_dist, "/home/ubuntu/dream")
    assert (
        command
        == "docker stack deploy "
           "-c /home/ubuntu/dream/docker-compose.yml "
           "-c /home/ubuntu/dream/assistant_dists/dream/docker-compose.override.yml "
           "-c /home/ubuntu/dream/assistant_dists/dream/proxy.yml -c /home/ubuntu/dream/assistant_dists/dream/dev.yml "
           "-c /home/ubuntu/dream/assistant_dists/dream/test_deployment.yml  dream"
    )
    assert (
        swarm_deployer_instance._get_docker_build_command_from_dist_configs
        == "docker-compose  "
           "-f /home/ubuntu/dream/docker-compose.yml "
           "-f /home/ubuntu/dream/assistant_dists/dream/docker-compose.override.yml "
           "-f /home/ubuntu/dream/assistant_dists/dream/proxy.yml "
           "-f /home/ubuntu/dream/assistant_dists/dream/dev.yml "
           "-f /home/ubuntu/dream/assistant_dists/dream/test_deployment.yml build"
    )
