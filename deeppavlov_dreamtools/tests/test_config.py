from pathlib import Path

from deeppavlov_dreamtools.distconfigs.assistant_dists import AssistantDist, DreamPipeline
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
    dream_dist_deepy.pipeline_conf.add_component(
        name="ner",
        component_group="annotators",
        definition=pipeline_conf_service_ner,
        inplace=True,
    )
    deepy_adv_ner = dream_dist_deepy.pipeline_conf.config.services.annotators["ner"]
    assert deepy_adv_ner, "Service `ner` couldn't be added via " "`add_service` method"

    assert deepy_adv_ner == pipeline_conf_service_ner, "Service differs from base service"
