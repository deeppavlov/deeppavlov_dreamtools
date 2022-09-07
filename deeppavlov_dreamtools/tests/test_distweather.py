from pathlib import Path

import pytest


@pytest.fixture(scope="module")
def dream_weather_dist_dir():
    """
    Path to directory where should be built files
    """
    dream_path_dist = Path().absolute().parents[2] / "dream" / "assistant_dists" / "dream_weather"
    yield dream_path_dist


@pytest.fixture(scope="module")
def files_in_dream_weather_dist_dir():
    """
    List of files in the dream_weather distribution directory
    """
    dream_path_dist = Path().absolute().parents[2] / "dream" / "assistant_dists" / "dream_weather"
    files = [file.name for file in dream_path_dist.iterdir()]
    yield files


@pytest.fixture(scope="module")
def dreamtools_dreamtools_dist_dir():
    """
    Path to dreamtools directory
    """
    dreamtools_dreamtools_dist_dir = Path().absolute().parents[0]
    yield dreamtools_dreamtools_dist_dir


def test_if_dream_weather_dist_exists(dream_weather_dist_dir) -> None:
    assert dream_weather_dist_dir.exists(), f"There is no directory on path: {dream_weather_dist_dir}"


@pytest.mark.parametrize("file", ["dev.yml", "docker-compose.override.yml", "pipeline_conf.json", "proxy.yml"])
def test_dist_file_in_dream_directory(file: str, dream_weather_dist_dir, files_in_dream_weather_dist_dir) -> None:
    assert file in files_in_dream_weather_dist_dir, f"The file {file} is not in the right directory"


@pytest.mark.parametrize("file", ["dev.yml", "docker-compose.override.yml", "pipeline_conf.json", "proxy.yml"])
def test_dream_weather_dist_corresponds_ground_truth_files(file: str, dream_weather_dist_dir,
                                                           dreamtools_dreamtools_dist_dir) -> None:
    """
    Test if built files are equal to ground-truth files that are based in `ground_truth_path`.
    If files aren't equal test shows which lines differ.

    Args:
        file (str): name of file
        dream_weather_dist_dir (Path): path to root Dream directory
        dreamtools_dreamtools_dist_dir (Path): path to nested deeppavlov_dreamtools directory
    """
    config_path = dream_weather_dist_dir / file
    ground_truth_path = dreamtools_dreamtools_dist_dir / "static" / "dream_weather_dist_configs" / file

    with open(ground_truth_path) as ground_truth_file:
        with open(config_path) as dist_file:

            ground_truth_text = ground_truth_file.readlines()
            dist_file_text = dist_file.readlines()
            differ_lines = []

            # check if lines[i] are equal
            for i in range(len(ground_truth_text)):
                if ground_truth_text[i] != dist_file_text[i]:
                    differ_lines.append(i + 1)

            assert (not differ_lines), f"built-file {file} differs from the ground_truth_file at lines: {differ_lines} "
