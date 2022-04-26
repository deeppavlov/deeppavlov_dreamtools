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
  skill  Create new basic skill template in ./skills
```

### dreamtools new dist
Create new dream dist
```
$ dreamtools new dist --help
Usage: dreamtools new dist [OPTIONS] NAME

  Create new distribution in ./assistant_dists with templates for docker-
  compose.override.yml, etc.

Options:
  --help  Show this message and exit.
```

### dreamtools new dff
Create new dff skill
```
$ dreamtools new dff --help
Usage: dreamtools new dff [OPTIONS] NAME

  Create new dff-based skill template in ./skills

Options:
  --help  Show this message and exit.
```

### dreamtools new skill
Create new skill
```
$ dreamtools new skill --help
Usage: dreamtools new skill [OPTIONS] NAME

  Create new basic skill template in ./skills

Options:
  --help  Show this message and exit.
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
