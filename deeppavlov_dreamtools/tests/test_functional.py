from pathlib import Path
import filecmp
import shutil

import pytest
from deeppavlov_dreamtools.tests.fixtures import (
    AssistantDist,
    dream_assistant_dists_dir,
    dream_root_dir,
    list_of_dream_dist,
    list_dists,
)


def test_list_dream_dist_is_not_empty(list_of_dream_dist):
    assert len(list_of_dream_dist) > 0


def test_items_in_dream_dist_is_DreamDist_objects(list_of_dream_dist):
    for dreamdist_item in list_of_dream_dist:
        assert isinstance(dreamdist_item, AssistantDist), f"{type(dreamdist_item)=} and {type(AssistantDist)=}"


def test_length_of_dreamdist_list_matches_the_number_of_directories(dream_root_dir, dream_assistant_dists_dir):
    count_of_dist_in_folder = 0
    dists = list_dists(dream_root_dir)
    for item in dists:
        if item.dist_path.is_dir():
            count_of_dist_in_folder += 1
    assert count_of_dist_in_folder == len(dists)


def test_discover_ports(dream_root_dir):
    dream_dist = AssistantDist.from_name("dream", dream_root_dir)

    assert dream_dist.compose_override.discover_port("personality-catcher") == 8010

    pipeline_service = dream_dist.pipeline_conf.config.services.skills["dff_program_y_skill"]
    assert dream_dist.pipeline_conf.discover_port(pipeline_service) == 8008

    assert dream_dist.compose_dev.discover_port("sentseg") == 8011

    assert dream_dist.compose_proxy.discover_port("sentrewrite") == 8017


def test_clone_dist(dream_root_dir):
    dream_dist = AssistantDist.from_name("dream", dream_root_dir)
    new_dist = dream_dist.clone(
        name="test_cloned_dream",
        display_name="test_clowned",
        description="Hell, purgatory, and heaven seem to differ the same as despair, fear, and assurance of salvation.",
    )
    config_files = [config.DEFAULT_FILE_NAME for config in dream_dist.iter_loaded_configs()]
    new_dist.save(overwrite=True)

    assert new_dist.dist_path.exists()

    mismatching_lines = []
    for config_filename in config_files:
        base_dist_config_filepath = dream_dist.dist_path / config_filename
        new_dist_config_filepath = new_dist.dist_path / config_filename

        with open(base_dist_config_filepath, "r") as base_f, open(new_dist_config_filepath, "r") as new_f:
            base_lines = base_f.readlines()
            new_lines = new_f.readlines()
            for i in range(len(new_lines)):
                base_line = base_lines[i].strip()
                new_line = new_lines[i].strip()
                if base_line.startswith('"display_name"') or base_line.startswith('"description"'):
                    continue
                if base_line != new_line:
                    mismatching_lines.append(f"{config_filename}: line {i}, {base_lines=}, {new_line=}")
        assert not mismatching_lines, mismatching_lines
