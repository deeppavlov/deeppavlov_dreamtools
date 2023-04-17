DELIMITER = "-" * 60

REQUIRED_CONFIG_NAMES = ["pipeline_conf.json", "docker-compose.override.yml"]
OPTIONAL_CONFIG_NAMES = ["dev.yml", "proxy.yml", "local.yml"]
ALL_CONFIG_NAMES = REQUIRED_CONFIG_NAMES + OPTIONAL_CONFIG_NAMES

COMPONENT_CARD_FILENAME = "component.yml"
COMPONENT_PIPELINE_FILENAME = "pipeline.yml"
COMPONENT_TEMPLATE_FILENAME = "template.yml"
