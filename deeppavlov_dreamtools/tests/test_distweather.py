from pathlib import Path

import pytest


@pytest.fixture(scope="module")
def dream_weather_dist_dir():
    dream_path_dist = Path(Path().absolute().parents[1]) / "dream" / "assistant_dists" / "dream_weather"
    yield dream_path_dist


@pytest.fixture(scope="module")
def files_in_dream_weather_dist_dir():
    dream_path_dist = Path().absolute().parents[1] / "dream" / "assistant_dists" / "dream_weather"
    files = [file.name for file in dream_path_dist.iterdir()]
    yield files


def test_if_dream_weather_dist_exists(dream_weather_dist_dir) -> None:
    assert dream_weather_dist_dir.exists(), f"There is no directory on path: {dream_weather_dist_dir}"


@pytest.mark.parametrize("file", ["dev.yml", "docker-compose.override.yml", "pipeline_conf.json", "proxy.yml"])
def test_dist_file_in_dream_directory(file: str, dream_weather_dist_dir, files_in_dream_weather_dist_dir) -> None:
    assert file in files_in_dream_weather_dist_dir, f"The file {file} is not in directory"


@pytest.mark.parametrize("file", ["dev.yml", "docker-compose.override.yml", "pipeline_conf.json", "proxy.yml"])
def test_dream_weather_dist_corresponds_ground_truth_files(file: str, dream_weather_dist_dir) -> None:
    """
    Test if built files are equal to ground-truth files that are based in `ground_truth_path`.

    Args:
        file (str): name of file
        dream_weather_dist_dir (Path): path to root Dream directory
    """
    config_path = dream_weather_dist_dir / file
    ground_truth_path = Path().absolute() / "static" / "dream_weather_dist_configs" / file
    with open(ground_truth_path) as ground_truth:
        with open(config_path) as dist_file:
            assert ground_truth.readlines() == dist_file.readlines(), f"built-file {file} differs from" \
                                                                      f" the ground_truth file"
