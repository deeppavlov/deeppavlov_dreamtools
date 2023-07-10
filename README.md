![coverage-badge](report/coverage.svg)
# Overview
dreamtools is a package which exposes high-level API for creating and editing Dream configuration files.

# Installation
Install from GitHub
```
pip install git+https://github.com/deeppavlov/deeppavlov_dreamtools.git --force-reinstall
```

or install in editable mode from cloned repo locally (useful for development purposes)
```
pip install -e .
```


# Package API
There are 4 main objects which represent Dream configurations

## Usage

### Quickstart
```python
from deeppavlov_dreamtools import AssistantDist, Pipeline, DreamComponent, DreamService


dist = AssistantDist.from_name("ai_faq_assistant", dream_root="/home/username/projects/dream")

new_dist = dist.clone(
    name="cloned_dist",
    display_name="Cloned AI FAQ Assistant",
    author="me@email.org",
    description="Yet another cloned assistant",
)

# common methods

# add component to distribution
component = DreamComponent.from_file("components/pGxj32ic41pvquRXUdqc7A.yml", dream_root="/home/username/projects/dream")
new_dist.add_component()

# save and generate new configs which include the annotator "spelling_preprocessing" added earlier
new_dist.save(overwrite=True, generate_configs=True)
# or generate configs separately
new_dist.generate_pipeline_conf()
new_dist.generate_compose()

# remove previously added component
new_dist.remove_component("annotators", "spelling_preprocessing")
new_dist.save(overwrite=True, generate_configs=True)
```
### AssistantDist
Represents distribution object.
You can either load it from classmethods `from_name`, `from_dist`
or initialize it directly passing underlying objects [see initializing from scratch](#Initializing-objects-from-scratch)

```python
from deeppavlov_dreamtools import AssistantDist

dist = AssistantDist.from_name("ai_faq_assistant", dream_root="/home/username/projects/dream")
```

### Pipeline
Represents pipeline object.
You can either load it from classmethod `from_name`
or initialize it directly passing underlying objects [see initializing from scratch](#Initializing-objects-from-scratch)

```python
from deeppavlov_dreamtools import Pipeline

pipeline = Pipeline.from_name("ai_faq_assistant", dream_root="/home/username/projects/dream")
```

### Component
Represents component object. Component is a part of Pipeline which describes how to interact with a service.
You can load it from classmethod `from_file`
```python
from deeppavlov_dreamtools import DreamComponent

component = DreamComponent.from_file("components/1Q9QXih1U2zhCpVm9zxdsA.yml", dream_root="/home/username/projects/dream")
```


### Service
Represents service object. Service is a part of Component which describes how to deploy a service.
Multiple components can use a single service.
You can load it from classmethods `from_config_dir`, `from_source_dir`
```python
from deeppavlov_dreamtools import DreamService

component = DreamService.from_config_dir(path="annotators/SentSeg/service_configs/sentseg", dream_root="/home/username/projects/dream")
```


### Initializing objects from scratch
```python
from deeppavlov_dreamtools import AssistantDist, Pipeline, DreamComponent, DreamService
from deeppavlov_dreamtools.distconfigs.generics import PipelineConfMetadata


dist = AssistantDist(
    dist_path="/home/username/projects/dream/assistant_dists/ai_faq_assistant",
    name="ai_faq_assistant",
    dream_root="/home/username/projects/dream",
    pipeline=Pipeline(
        config=None,
        metadata=PipelineConfMetadata(
            display_name="AI FAQ Assistant",
            author="me@email.org",
            description="Answers FAQ Questions",
        ),
        annotators={
            "sentseg": DreamComponent.from_file("components/gM4fEjvVqLlSRRRkQfds2g.yml", "/home/username/projects/dream"),
            "prompt_goals_collector": DreamComponent.from_file("components/fOud1KbT6qhY.yml", "/home/username/projects/dream"),
            "prompt_selector": DreamComponent.from_file("components/fOud1KbT6qhY.yml", "/home/username/projects/dream"),
        },
        skills={
            "dff_ai_faq_prompted_skill": DreamComponent.from_file("components/sQjaqWKJjVWjVEIbNuA.yml", "/home/username/projects/dream"),
            "dummy_skill": DreamComponent.from_file("components/uYkoK0vRp4bbIg9akI1yw.yml", "/home/username/projects/dream"),
        },
        response_selectors={
            "response_selector": DreamComponent.from_file("components/YJzc7NwGrLmKp6gfZJh7X1.yml", "/home/username/projects/dream")
        },
        last_chance_service=DreamComponent.from_file("components/70NLr5qqOow5.yml", "/home/username/projects/dream"),
        timeout_service=DreamComponent.from_file("components/x8rLTpIWct4P.yml", "/home/username/projects/dream"),
        response_annotators={
            "sentseg": DreamComponent.from_file("components/1Q9QXih1U2zhCpVm9zxdsA.yml", "/home/username/projects/dream"),
        },
        response_annotator_selectors=DreamComponent.from_file("components/LXrJDIf43gwNmPMNXG5Eg.yml", "/home/username/projects/dream"),
        candidate_annotators={
            "combined_classification": DreamComponent.from_file("components/PbLNvh4hrvs47rPaf2bfYQ.yml", "/home/username/projects/dream"),
            "sentence_ranker": DreamComponent.from_file("components/XGwmAHtAOu0NDqqG3QCJw.yml", "/home/username/projects/dream"),
        },
        skill_selectors={
            "description_based_skill_selector": DreamComponent.from_file("components/dfsw4bji8bgjq2.yml", "/home/username/projects/dream"),
        },
        services={
            "transformers_lm_oasst12b": DreamComponent.from_file("component/sdkajfhsidhf8wfjh2ornfkle.yml", "/home/username/projects/dream")
        },
    ),
)

# save and generate configs
dist.save(overwrite=True, generate_configs=True)
```

# Command Line Interface
dreamtools support a number of commands to ease Dream development.
You can always refer to
`dreamtools {command} --help`
or
`dreamtools {command} {subcommand} --help`
to see available arguments.

- [dreamtools](#dreamtools)
  - new
    - [dist](#dreamtools-new-dist)
  - clone
    - [dist](#dreamtools-clone-dist)
  - add
    - [component](#dreamtools-add-component)

# dreamtools
All CLI commands start with the main command `dreamtools`.
You can either call it from inside the cloned Dream directory or provide it as an argument:

```
dreamtools -D home/username/projects/dream {command} {subcommand} ...
```

### dreamtools new dist
Create new Dream distribution

```
dreamtools new dist my_assistant \
  --display-name "My Assistant" \
  --author myemail@email.org \
  --description "My custom Distribution" \
  --annotators components/1Q9QXih1U2zhCpVm9zxdsA.yml \
  --annotators components/dflkgjdlkh342r9ndf.yml \
  --annotators components/tgzaSQggV7wgMprOmF1Ww.yml \
  --annotators components/M1sE6hOm20EGBWBdr0vIOw.yml \
  --annotators components/O4FVnkAwjay1mL1FbuRGWw.yml \
  --skills components/4yA8wZWOEnafRfz6Po9nvA.yml \
  --skills components/qx0j5QHAzog0b39nRnuA.yml \
  --skills components/ckUclxqUplyzwmnYyixEw.yml \
  --skills components/uYkoK0vRp4bbIg9akI1yw.yml \
  --response-annotators components/dflkgjdlkh342r9ndf.yml \
  --response-annotators components/05PqJXVd7gV7DqslN5z3A.yml \
  --last-chance-service components/70NLr5qqOow5.yml \
  --timeout-service components/x8rLTpIWct4P.yml \
  --response-annotator-selectors components/LXrJDIf43gwNmPMNXG5Eg.yml \
  --skill-selectors components/xSwFvtAUdvtQosvzpb7oMg.yml \
  --response-selectors components/KX4drAocVa5APcivWHeBNQ.yml \
  --overwrite
```


### dreamtools clone dist
Clone existing (--template argument) distribution

```
dreamtools clone dist dream_adventurer_openai_prompted \
--template dream_persona_openai_prompted \
--display-name "Dream Adventurer" \
--author deepypavlova@email.org \
--description "This is a simple dialog system that can chat with you on any topic. It has a pre-defined personality and uses OpenAI ChatGPT model to generate responses." \
--overwrite
```


### dreamtools add component
Add component from component card to distribution

```
dreamtools add component components/jkdhfgkhgodfiugpojwrnkjnlg.yml --dist dream_persona_openai_prompted
```
