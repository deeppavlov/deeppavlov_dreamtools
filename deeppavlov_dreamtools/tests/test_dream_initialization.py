import pytest
from deeppavlov_dreamtools.distconfigs.manager import (
    DreamComposeDev,
    DreamComposeOverride,
    DreamComposeProxy,
    AssistantDist,
    DreamPipeline,
)
from deeppavlov_dreamtools.tests.fixtures import (
    dream_assistant_dists_dir,
    dream_root_dir,
)


@pytest.mark.parametrize(
    "dist,config_classes",
    [
        (
            "dream",
            [DreamPipeline, DreamComposeOverride, DreamComposeDev, DreamComposeProxy],
        ),
        ("deepy_base", [DreamPipeline, DreamComposeOverride]),
        ("deepy_adv", [DreamPipeline, DreamComposeOverride]),
        ("deepy_faq", [DreamPipeline, DreamComposeOverride]),
    ],
)
def test_dream_configs_classmethods(dream_assistant_dists_dir, dist, config_classes):
    dist_path = dream_assistant_dists_dir / dist

    for config_class in config_classes:
        config_from_path = config_class.from_path(dist_path / config_class.DEFAULT_FILE_NAME)
        config_from_dist = config_class.from_dist(dist_path)

        assert config_from_path.config == config_from_dist.config


def test_dream_dist_classmethods(dream_assistant_dists_dir, dream_root_dir):
    dist_name = "dream"
    dist_path = dream_assistant_dists_dir / dist_name

    dream_dist_from_dist = AssistantDist.from_dist(dist_path, compose_local=False)
    dream_dist_from_name = AssistantDist.from_name(dist_name, dream_root_dir, compose_local=False)

    for config_from_dist, config_from_name in zip(
        dream_dist_from_dist.iter_loaded_configs(),
        dream_dist_from_name.iter_loaded_configs(),
    ):
        assert config_from_dist.config == config_from_name.config
