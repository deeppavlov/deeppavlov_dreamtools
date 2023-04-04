from pathlib import Path

import pytest
from deeppavlov_dreamtools import AssistantDist
from deeppavlov_dreamtools.distconfigs import list_dists
from deeppavlov_dreamtools.tests.fixtures import (
    create_weather_dist,
    dream_weather_dist_dir,
    files_in_dream_weather_dist_dir,
    list_of_dream_dist,
)


@pytest.fixture
def dream_root_dir(pytestconfig):
    yield Path(pytestconfig.getoption("dream_root"))


@pytest.fixture
def create_weather_dist(dream_root_dir):
    template_name = "dream"
    name = "dream_weather"
    services = [
        "convers-evaluator-annotator",
        "spacy-nounphrases",
        "convers-evaluator-selector",
        "dff-intent-responder-skill",
        "intent-catcher",
        "ner",
        "entity-detection",
        "dff-weather-skill",
        "dialogpt",
    ]
    pipeline_conf = True
    compose_override = True
    compose_dev = True
    compose_proxy = True
    compose_local = False
    overwrite = True

    dream_dist = AssistantDist.from_name(
        template_name,
        dream_root_dir,
        pipeline_conf,
        compose_override,
        compose_dev,
        compose_proxy,
        compose_local,
    )
    new_dist = dream_dist._create_dist(
        name,
        dream_root_dir,
        services,
        pipeline_conf,
        compose_override,
        compose_dev,
        compose_proxy,
        compose_local,
    )
    pass

    paths = new_dist.save(overwrite)

    yield paths


@pytest.fixture
def dream_weather_dist_dir(create_weather_dist, dream_root_dir):
    """
    Path to directory where should be built files
    """
    dream_path_dist = dream_root_dir / "assistant_dists" / "dream_weather"
    yield dream_path_dist


@pytest.fixture
def files_in_dream_weather_dist_dir(dream_weather_dist_dir):
    """
    List of files in the dream_weather distribution directory
    """
    files = [file.name for file in dream_weather_dist_dir.iterdir()]
    yield files


def test_if_dream_weather_dist_exists(dream_weather_dist_dir) -> None:
    assert dream_weather_dist_dir.exists(), f"There is no directory at path: {dream_weather_dist_dir}"


@pytest.mark.parametrize(
    "file",
    ["dev.yml", "docker-compose.override.yml", "pipeline_conf.json", "proxy.yml"],
)
def test_dist_file_in_dream_directory(file: str, dream_weather_dist_dir, files_in_dream_weather_dist_dir) -> None:
    assert file in files_in_dream_weather_dist_dir, f"The file {file} is not in the right directory"


@pytest.mark.parametrize(
    "file",
    # ["dev.yml", "docker-compose.override.yml", "pipeline_conf.json", "proxy.yml"],
    ["dev.yml", "docker-compose.override.yml", "proxy.yml"],
)
def test_dream_weather_dist_corresponds_ground_truth_files(file: str, dream_weather_dist_dir) -> None:
    """
    Test if built files are equal to ground-truth files that are based in `ground_truth_path`.
    If files aren't equal test shows which lines differ and prints those two different lines.

    Args:
        file (str): name of file
        dream_weather_dist_dir (Path): path to root Dream directory
    """
    config_path = dream_weather_dist_dir / file
    ground_truth_path = Path(__file__).parents[1] / "static" / "dream_weather_dist_configs" / file

    with open(ground_truth_path) as ground_truth_file:
        with open(config_path) as dist_file:
            ground_truth_text = ground_truth_file.readlines()
            dist_file_text = dist_file.readlines()
            differ_lines = []

            # check if lines[i] are equal
            for i in range(len(ground_truth_text)):
                if ground_truth_text[i] != dist_file_text[i]:
                    print(f"{ground_truth_text[i]} != {dist_file_text[i]}")
                    differ_lines.append(i + 1)
            assert not differ_lines, f"built-file {file} differs from the ground_truth_file at lines: {differ_lines} "
