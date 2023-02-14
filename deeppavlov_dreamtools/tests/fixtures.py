from pathlib import Path

import pytest
from deeppavlov_dreamtools.distconfigs import AssistantDist, list_dists, const


@pytest.fixture
def dream_root_dir(pytestconfig):
    yield Path(pytestconfig.getoption("dream_root"))


@pytest.fixture
def dream_assistant_dists_dir(dream_root_dir):
    yield dream_root_dir / const.ASSISTANT_DISTS_DIR_NAME


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
    new_dist = dream_dist.create_dist(
        name,
        dream_root_dir,
        services,
        pipeline_conf,
        compose_override,
        compose_dev,
        compose_proxy,
        compose_local,
    )
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


@pytest.fixture
def list_of_dream_dist(dream_root_dir):
    yield list_dists(dream_root_dir)


@pytest.fixture
def list_of_assistant_dists(dream_assistant_dists_dir):
    yield [file.name for file in dream_weather_dist_dir.iterdir()]
