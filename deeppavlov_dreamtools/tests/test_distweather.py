from pathlib import Path

import pytest
from deeppavlov_dreamtools import DreamDist
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


def test_if_dream_weather_dist_exists(dream_weather_dist_dir) -> None:
    assert (
        dream_weather_dist_dir.exists()
    ), f"There is no directory at path: {dream_weather_dist_dir}"


@pytest.mark.parametrize(
    "file",
    ["dev.yml", "docker-compose.override.yml", "pipeline_conf.json", "proxy.yml"],
)
def test_dist_file_in_dream_directory(
    file: str, dream_weather_dist_dir, files_in_dream_weather_dist_dir
) -> None:
    assert (
        file in files_in_dream_weather_dist_dir
    ), f"The file {file} is not in the right directory"


@pytest.mark.parametrize(
    "file",
    ["dev.yml", "docker-compose.override.yml", "pipeline_conf.json", "proxy.yml"],
)
def test_dream_weather_dist_corresponds_ground_truth_files(
    file: str, dream_weather_dist_dir
) -> None:
    """
    Test if built files are equal to ground-truth files that are based in `ground_truth_path`.
    If files aren't equal test shows which lines differ and prints those two different lines.

    Args:
        file (str): name of file
        dream_weather_dist_dir (Path): path to root Dream directory
    """
    config_path = dream_weather_dist_dir / file
    ground_truth_path = (
        Path(__file__).parents[1] / "static" / "dream_weather_dist_configs" / file
    )

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

            assert (
                not differ_lines
            ), f"built-file {file} differs from the ground_truth_file at lines: {differ_lines} "
