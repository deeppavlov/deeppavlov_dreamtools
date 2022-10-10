import pytest
from deeppavlov_dreamtools.distconfigs.manager import (
    DreamComposeDev,
    DreamComposeOverride,
    DreamComposeProxy,
    DreamDist,
    DreamPipeline,
)
from deeppavlov_dreamtools.tests.fixtures import dream_assistant_dist_dir, dream_root_dir

PIPELINE_CONF_FILENAME = "pipeline_conf.json"
OVERRIDE_FILENAME = "docker-compose.override.yml"
DEV_FILENAME = "dev.yml"
PROXY_FILENAME = "proxy.yml"

DISTRIBUTION_NAMES = [
    "deepy_adv",
    "deepy_base",
    "deepy_faq",
]


@pytest.mark.parametrize(
    "dist",
    DISTRIBUTION_NAMES,
)
def test_dream_configs_initialization_through__from_path__method(dist, dream_assistant_dist_dir, dream_root_dir):
    dist_path = dream_assistant_dist_dir / dist
    filenames = [file.name for file in dist_path.iterdir()]

    pipeline_conf, compose_override, compose_dev, compose_proxy = None, None, None, None

    if PIPELINE_CONF_FILENAME in filenames:
        pipeline_conf = DreamPipeline.from_path(dist_path / PIPELINE_CONF_FILENAME)
    if OVERRIDE_FILENAME in filenames:
        compose_override = DreamComposeOverride.from_path(dist_path / OVERRIDE_FILENAME)
    if DEV_FILENAME in filenames:
        compose_dev = DreamComposeDev.from_path(dist_path / DEV_FILENAME)
    if PROXY_FILENAME in filenames:
        compose_proxy = DreamComposeProxy.from_path(dist_path / PROXY_FILENAME)

    assert pipeline_conf, f"{PIPELINE_CONF_FILENAME} couldn't be initialized through method `from_path`"
    assert compose_override, f"{OVERRIDE_FILENAME} couldn't be initialized through method `from_path`"
    assert compose_proxy, f"{PROXY_FILENAME} couldn't be initialized through method `from_path`"
    assert compose_dev, f"{DEV_FILENAME} couldn't be initialized through method `from_path`"


@pytest.mark.parametrize(
    "dist",
    DISTRIBUTION_NAMES,
)
def test_dream_dist_object_initialization_through_constructor(dist, dream_assistant_dist_dir, dream_root_dir):
    dist_path = dream_assistant_dist_dir / dist
    filenames = [file.name for file in dist_path.iterdir()]

    pipeline_conf, compose_override, compose_dev, compose_proxy = None, None, None, None
    if PIPELINE_CONF_FILENAME in filenames:
        pipeline_conf = DreamPipeline.from_dist(dist_path)
    if OVERRIDE_FILENAME in filenames:
        compose_override = DreamComposeOverride.from_dist(dist_path)
    if DEV_FILENAME in filenames:
        compose_dev = DreamComposeDev.from_dist(dist_path)
    if PROXY_FILENAME in filenames:
        compose_proxy = DreamComposeProxy(dist_path)

    assert DreamDist(
        dist_path=dist_path,
        name=dist,
        dream_root=dream_root_dir,
        pipeline_conf=pipeline_conf,
        compose_override=compose_override,
        compose_dev=compose_dev,
        compose_proxy=compose_proxy,
    ), f"The distribution {dist} couldn't be initialized through constructor"


@pytest.mark.parametrize(
    "dist",
    DISTRIBUTION_NAMES,
)
def test_dream_dist_object_initialization_through__from_dist__method(dist, dream_assistant_dist_dir):
    dist_path = dream_assistant_dist_dir / dist
    filenames = [file.name for file in dist_path.iterdir()]

    dream_dist = DreamDist.from_dist(
        dist_path=dist_path,
        pipeline_conf="pipeline_conf.json" in filenames,
        compose_override="docker-compose.override.yml" in filenames,
        compose_dev="dev.yml" in filenames,
        compose_proxy="proxy.yml" in filenames,
        compose_local="local.yml" in filenames,
    )

    assert dream_dist, f"The distribution {dist} couldn't be initialized through method `from_dist`"
