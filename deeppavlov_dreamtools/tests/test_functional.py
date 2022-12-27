from pathlib import Path

import pytest
from deeppavlov_dreamtools.tests.fixtures import (
    DreamDist,
    dream_assistant_dists_dir,
    dream_root_dir,
    list_of_dream_dist,
)


def test_list_dream_dist_is_not_empty(list_of_dream_dist):
    assert len(list_of_dream_dist) > 0


def test_items_in_dream_dist_is_DreamDist_objects(list_of_dream_dist):
    for dreamdist_item in list_of_dream_dist:
        assert isinstance(dreamdist_item, DreamDist), f"{type(dreamdist_item)=} and {type(DreamDist)=}"


def test_length_of_dreamdist_list_matches_the_number_of_directories(list_of_dream_dist, dream_assistant_dists_dir):
    count_of_dist_in_folder = 0
    for item in dream_assistant_dists_dir.iterdir():
        if item.is_dir():
            count_of_dist_in_folder += 1
    assert count_of_dist_in_folder == len(list_of_dream_dist)


def test_discover_ports(dream_root_dir):
    dream_dist = DreamDist.from_name("dream", dream_root_dir)

    assert dream_dist.compose_override.discover_port("personality-catcher") == 8010

    pipeline_service = dream_dist.pipeline_conf.config.services.skills["dff_program_y_skill"]
    assert dream_dist.pipeline_conf.discover_port(pipeline_service) == 8008

    assert dream_dist.compose_dev.discover_port("sentseg") == 8011

    assert dream_dist.compose_proxy.discover_port("sentrewrite") == 8017
