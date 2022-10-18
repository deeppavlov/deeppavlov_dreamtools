![coverage-badge](report/coverage.svg)

# Installation
```
pip install -e .
```

# Command hierarchy
- [dreamtools](#dreamtools)
  - [new](#dreamtools-new)
    - [dist](#dreamtools-new-dist)
    - [dff](#dreamtools-new-dff)
    - [skill](#dreamtools-new-skill)
    - [local](#dreamtools-new-local)
  - [test](#dreamtools-test)
    - [api](#dreamtools-test-api)
  - [verify](#dreamtools-verify)
    - [dist](#dreamtools-verify-dist)
    - [dff](#dreamtools-verify-dff)
    - [downloads](#dreamtools-verify-downloads)
    
# dreamtools
```
$ dreamtools --help
Usage: dreamtools [OPTIONS] COMMAND [ARGS]...

  dreamtools is a command line utility which enhances your DeepPavlov Dream
  development experience

Options:
  -D, --dream DIRECTORY  Dream root directory. Defaults to ./
  --help                 Show this message and exit.

Commands:
  new     Create new template for distribution or skill
  test    Test something
  verify  Verify distribution or skill
```

## dreamtools new
```
$ dreamtools new --help
Usage: dreamtools new [OPTIONS] COMMAND [ARGS]...

  Create new template for distribution or skill

Options:
  --help  Show this message and exit.

Commands:
  dff    Create new dff-based skill template in ./skills
  dist   Create new distribution in ./assistant_dists with templates for...
  local  Create new local.yml
```

### dreamtools new dist
Create new dream dist
```
$ dreamtools new dist --help
Usage: dreamtools new dist [OPTIONS] NAME

  Creates new distribution in ./assistant_dists

Options:
  -d, --dist TEXT                 Dream distribution name
  -s, --services TEXT             Dream distribution name
  --overwrite / --no-overwrite    Overwrite distribution directory if it
                                  exists
  --all                           Create all configs (defaults to False).
                                  Overrides --pipeline and all other
                                  --compose-* flags
  --pipeline / --no-pipeline      Create pipeline_conf.json config (defaults
                                  to True)
  --compose-override / --no-compose-override
                                  Create docker-compose.override.yml config
                                  (defaults to False)
  --compose-dev / --no-compose-dev
                                  Create dev.yml config (defaults to False)
  --compose-proxy / --no-compose-proxy
                                  Create proxy.yml config (defaults to False)
  --compose-local / --no-compose-local
                                  Create local.yml config (defaults to False)
  --help                          Show this message and exit.
```

### dreamtools new dff
Create new dff skill
```
$ dreamtools new dff --help
Usage: dreamtools new dff [OPTIONS] NAME

  Creates new dff skill in ./skills

Options:
  -d, --dist TEXT                 Dream distribution name  [required]
  -p, --port TEXT                 DFF skill port  [required]
  --all                           Add definition to all docker-compose configs
                                  (defaults to False). Overrides all other
                                  --compose-* flags
  --compose-override / --no-compose-override
                                  Add definition to docker-
                                  compose.override.yml (defaults to False)
  --compose-dev / --no-compose-dev
                                  Add definition to dev.yml config (defaults
                                  to False)
  --compose-proxy / --no-compose-proxy
                                  Add definition to proxy.yml config (defaults
                                  to False)
  --compose-local / --no-compose-local
                                  Add definition to local.yml config (defaults
                                  to False)
  --help                          Show this message and exit.
```

### dreamtools new local
Create new local.yml. Replacement for `dream/utils/create_local_yml.py`
```
$ dreamtools new local --help
Usage: dreamtools new local [OPTIONS] NAME

  Create new local.yml

Options:
  --help  Show this message and exit.
```

## dreamtools test
```
$ dreamtools test --help
Usage: dreamtools test [OPTIONS] COMMAND [ARGS]...

  Test something

Options:
  --help  Show this message and exit.

Commands:
  api  Test api
```

### dreamtools test api
Test api. Replacement for `dream/utils/http_api_test.py` and `dream/utils/xlsx_responder.py` (probably)
```dreamtools test api --help
Usage: dreamtools test api [OPTIONS] NAME

  Test api

Options:
  --xlsx
  --help  Show this message and exit.
```

## dreamtools verify
```
$ dreamtools verify --help
Usage: dreamtools verify [OPTIONS] COMMAND [ARGS]...

  Verify distribution or skill

Options:
  --help  Show this message and exit.

Commands:
  dff        Verify dff skill
  dist       Verify distribution
  downloads  Verify downloads
```

### dreamtools verify dist
Verify dist. Replacement for `dream/utils/verify_compose.py` and more.
```$ dreamtools verify dist --help
Usage: dreamtools verify dist [OPTIONS] NAME

  Verify distribution

Options:
  --help  Show this message and exit.
```

### dreamtools verify dff
Verify dff skill
```$ dreamtools verify dff --help
Usage: dreamtools verify dff [OPTIONS] NAME

  Verify dff skill

Options:
  --help  Show this message and exit.
```

### dreamtools verify downloads
Verify downloads. Replacement for `dream/utils/analyze_downloads.py` and more.
```$ dreamtools verify downloads --help
Usage: dreamtools verify downloads [OPTIONS] NAME

  Verify downloads

Options:
  --help  Show this message and exit.
```
