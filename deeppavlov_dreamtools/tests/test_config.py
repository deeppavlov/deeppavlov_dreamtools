import shutil
from pathlib import Path

from deeppavlov_dreamtools.distconfigs.assistant_dists import AssistantDist, DreamPipeline, DreamComposeOverride
from deeppavlov_dreamtools.tests.fixtures import dream_root_dir


def test_add_service_to_dreampipeline(dream_root_dir: Path):
    """
    Test add_service function of DreamPipeline
    We extract ner service from dream distribution with name `dream` to `deepy_adv` distribution.
    """
    dream_dist_deepy = AssistantDist.from_name(
        name="deepy_adv", dream_root=dream_root_dir, compose_dev=False, compose_local=False, compose_proxy=False
    )
    dream_dist_dream = AssistantDist.from_name(name="dream", dream_root=dream_root_dir, compose_local=False)

    pipeline_conf_service_ner = dream_dist_dream.pipeline_conf.config.services.annotators["ner"]
    dream_dist_deepy.pipeline_conf.add_service(
        name="ner",
        service_type="annotators",
        definition=pipeline_conf_service_ner,
        inplace=True,
    )
    deepy_adv_ner = dream_dist_deepy.pipeline_conf.config.services.annotators["ner"]
    assert deepy_adv_ner, "Service `ner` couldn't be added via " "`add_service` method"

    assert deepy_adv_ner == pipeline_conf_service_ner, "Service differs from base service"


def test_add_yml_config_to_another(dream_root_dir):
    dist = AssistantDist.from_name("dream", dream_root_dir)
    field_names = ["environment", "volumes", "ports", "env_file"]
    override = dist.compose_override
    dev = dist.compose_dev
    proxy = dist.compose_proxy
    compose_union = dev + proxy + override

    for config in [dev, proxy, override]:
        for service_name, service in config.iter_services():
            service_union = compose_union.get_service(service_name)
            for field_name in field_names:
                field_config = getattr(config.get_service(service_name), field_name)
                field_res = getattr(service_union, field_name)

                if field_config and not field_res:
                    assert False
                if field_config and field_res:
                    if not all(elem in field_res for elem in field_config):
                        assert False


def test_merge_env_fieild(dream_root_dir):
    dist = AssistantDist.from_name("dream", dream_root_dir)
    co = dist.compose_override._merge_env_fields([1, 2], [3, 2])
    assert co == [1, 3, 2]


def test_move_content_of_env_file_to_environment_field(dream_root_dir):
    dist = AssistantDist.from_name("dream", dream_root_dir)
    dist.name = "testenv_dream"
    dist.compose_override: DreamComposeOverride = dist.compose_override.filter_services(["dff-program-y-skill"])[1]
    dist.compose_override.config.services["dff-program-y-skill"].env_file = [
        dist.dist_path / "one.env",
        dist.dist_path / "two.env",
    ]
    dist.save(overwrite=True)
    with open(dist.dist_path / "one.env", "w") as f:
        f.write("ENV1=1\n")
        f.write("ENV2=2")
    with open(dist.dist_path / "two.env", "w") as f:
        f.write("ENV3=3\n")
        f.write("ENV2=test")

    dist.compose_override.move_content_of_env_file_to_environment_field()
    try:
        assert dist.compose_override.config.services["dff-program-y-skill"].environment == [
            "ENV1=1",
            "ENV2=test",
            "ENV3=3",
        ]
    except AssertionError as e:
        shutil.rmtree(dist.dist_path)
        raise e
