from pathlib import Path
from typing import List

import pytest

from deeppavlov_dreamtools.tests.fixtures import list_of_dream_dist, dream_root_dir
from deeppavlov_dreamtools.distconfigs.assistant_dists import AssistantDist, PipelineConfService
from deeppavlov_dreamtools.deployer.swarm import SwarmDeployer


@pytest.fixture
def swarm_deployer_instance():
    swarm_deployer = SwarmDeployer(
        user_identifier="test", portainer_key=None, portainer_url=None
    )
    yield swarm_deployer


def test_get_url_prefixed(dream_root_dir):
    service: PipelineConfService = AssistantDist.from_name(
        name="dream", dream_root=dream_root_dir
    ).pipeline_conf.config.services.annotators["spelling_preprocessing"]
    service.connector.url = SwarmDeployer.get_url_prefixed(service.connector.url, "test_")
    assert service.connector.url == "http://test_spelling-preprocessing:8074/respond"


def test_change_pipeline_conf_services_url_for_deployment(
    swarm_deployer_instance, list_of_dream_dist: List[AssistantDist]
):
    for dream_dist in list_of_dream_dist:
        swarm_deployer_instance._change_pipeline_conf_services_url_for_deployment(dream_dist.pipeline_conf, "test_")
        for _, service_name, service in dream_dist.pipeline_conf.iter_services():
            try:
                url = service.connector.url
            except AttributeError:
                continue
            if url is None or service_name == "mongo":
                continue

            assert url.startswith("http://main_")


def test_create_yml_file_with_explicit_images_in_local_dist(dream_root_dir, swarm_deployer_instance):
    dream_dist = AssistantDist.from_name(dream_root=dream_root_dir, name="dream")
    swarm_deployer_instance._create_deployment_yml_file(dream_dist)
    dream_dist_path = dream_dist.dist_path
    filepath = dream_dist_path / "test_deployment.yml"
    assert filepath.exists()
    # check if file isn't empty
    assert filepath.stat().st_size > 0


def test_swarmdeployer_commands(dream_root_dir, swarm_deployer_instance):
    dream_dist = AssistantDist.from_name(dream_root=dream_root_dir, name="dream")
    command = swarm_deployer_instance._get_docker_build_command_from_dist_configs(
        dream_dist, Path("/home/ubuntu/dream")
    )
    assert (
        command == "docker compose "
        "-f /home/ubuntu/dream/docker-compose.yml "
        "-f /home/ubuntu/dream/assistant_dists/dream/docker-compose.override.yml "
        "-f /home/ubuntu/dream/assistant_dists/dream/dev.yml "
        "-f /home/ubuntu/dream/assistant_dists/dream/test_deployment.yml build"
    )


def test_get_image_names_of_the_dist(dream_root_dir, swarm_deployer_instance):
    deepy_base_dist = AssistantDist.from_name("deepy_base", dream_root_dir)
    _, deepy_base_dist.compose_override = deepy_base_dist.compose_override.filter_services(
        ["agent", "harvesters-maintenance-skill"]
    )
    assert swarm_deployer_instance._get_image_names_of_the_dist(deepy_base_dist) == [
        "deepy_base_agent",
        "deepy_base_harvesters-maintenance-skill",
    ]


def test_change_waithosts_url(swarm_deployer_instance, dream_root_dir):
    deepy_base_dist = AssistantDist.from_name("deepy_base", dream_root_dir)
    swarm_deployer_instance._change_waithosts_url(deepy_base_dist.compose_override, "")
    answer = (
        "main_spelling-preprocessing:8074, main_harvesters-maintenance-skill:3662, "
        "main_rule-based-response-selector:8005, main_emotion-classification-deepy:8015, "
        "main_dff-program-y-skill:8008"
    )
    assert deepy_base_dist.compose_override.config.services["agent"].environment["WAIT_HOSTS"] == answer


def test_leave_only_user_services(swarm_deployer_instance, dream_root_dir):
    deepy_base_dist = AssistantDist.from_name("deepy_base", dream_root_dir)
    swarm_deployer_instance.user_services = ["agent", "spelling-preprocessing"]
    swarm_deployer_instance._leave_only_user_services(deepy_base_dist)
    service_names = [service_name for service_name, _ in deepy_base_dist.compose_override.iter_services()]
    assert service_names == ["agent", "spelling-preprocessing"]


def test_remove_mongo_service_in_dev(swarm_deployer_instance, dream_root_dir):
    deepy_base_dist = AssistantDist.from_name("deepy_base", dream_root_dir)
    dream_dist = AssistantDist.from_name("dream", dream_root_dir)

    swarm_deployer_instance._remove_mongo_service_in_dev(deepy_base_dist)
    swarm_deployer_instance._remove_mongo_service_in_dev(dream_dist)
    assert not dream_dist.compose_dev.get_service("mongo")
