import pytest
from pathlib import Path

from deeppavlov_dreamtools.distconfigs.manager import (
    DreamDist,
    DreamPipeline,
    DreamComposeOverride,
    DreamComposeDev,
    DreamComposeProxy,
    DreamComposeLocal,
)
from deeppavlov_dreamtools.distconfigs.const import ASSISTANT_DISTS_DIR_NAME

from deeppavlov_dreamtools.tests.fixtures import (
    dream_root_dir,
    list_of_dream_dist,
    list_of_assistant_dists,
    dream_assistant_dists_dir,
)


def test_load_configs_with_default_filenames(list_of_dream_dist: list, dream_assistant_dists_dir: Path):
    """
    Check if load_configs_with_default_filenames method loads and initialize configs properly

    """
    for dream_dist in list_of_dream_dist:
        dist_name = dream_dist.name
        dist_path = dream_assistant_dists_dir / dist_name

        filenames_in_dist = [file.name for file in dist_path.iterdir()]

        pipeline_in_dist: bool = "pipeline_conf.json" in filenames_in_dist
        override_in_dist: bool = "docker-compose.override.yml" in filenames_in_dist
        dev_in_dist: bool = "dev.yml" in filenames_in_dist
        proxy_in_dist: bool = "proxy.yml" in filenames_in_dist
        local_in_dist: bool = "local.yml" in filenames_in_dist

        configs = DreamDist.load_configs_with_default_filenames(
            dist_path=dist_path,
            pipeline_conf=pipeline_in_dist,
            compose_override=override_in_dist,
            compose_dev=dev_in_dist,
            compose_proxy=proxy_in_dist,
            compose_local=local_in_dist,
        )
        try:
            if pipeline_in_dist:
                pipeline_conf = configs["pipeline_conf"]
                assert pipeline_conf
                assert isinstance(pipeline_conf, DreamPipeline)

            if override_in_dist:
                compose_override = configs["compose_override"]
                assert compose_override
                assert isinstance(compose_override, DreamComposeOverride)

            if dev_in_dist:
                compose_dev = configs["compose_dev"]
                assert compose_dev
                assert isinstance(compose_dev, DreamComposeDev)

            if proxy_in_dist:
                compose_proxy = configs["compose_proxy"]
                assert compose_proxy
                assert isinstance(compose_proxy, DreamComposeProxy)

            if local_in_dist:
                compose_local = configs["compose_local"]
                assert compose_local
                assert isinstance(compose_local, DreamComposeLocal)

        except KeyError:
            KeyError(f"The config object doesn't have one or more config")


def test_dreamdist_save(list_of_dream_dist: list[DreamDist], dream_assistant_dists_dir: Path):
    """
    Changes name and dist_path of dreamdist and then compare configs of new and base distributions
    """
    for dream_dist in list_of_dream_dist:

        test_name = dream_dist.name + "_test"
        dream_dist.name = test_name
        dream_dist.dist_path = dream_assistant_dists_dir / test_name
        dream_dist.save()

        path_to_test_dir = dream_assistant_dists_dir / test_name

        assert path_to_test_dir.exists()
        assert path_to_test_dir.is_dir()

        for config in dream_dist.iter_loaded_configs():
            with open(path_to_test_dir / config.DEFAULT_FILE_NAME, "r") as test:
                with open(dream_dist.dist_path / config.DEFAULT_FILE_NAME, "r") as base:
                    differ_lines = []

                    test_lines = test.readlines()
                    base_lines = base.readlines()
                    for i in range(len(test_lines)):
                        if test_lines[i].strip() != base_lines[i].strip():
                            print(f"`{test_lines[i]}` != `{base_lines[i]}`\n")
                            differ_lines.append(test_lines[i])
            assert not differ_lines, f"{differ_lines}"
