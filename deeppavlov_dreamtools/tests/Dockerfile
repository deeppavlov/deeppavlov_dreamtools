FROM python:3.10.5-slim

WORKDIR /usr/src/app

RUN git clone https://github.com/deeppavlovteam/dream & git clone https://github.com/deeppavlovteam/deeppavlov_dreamtools

RUN pip install -r  --no-cache deeppavlov_dreamtools/requirements.txt

COPY ../../deeppavlov_dreamtools/tests/* ./deeppavlov_dreamtools/deeppavlov_dreamtools/tests

RUN pip install -r  --no-cache /deeppavlov_dreamtools/tests/requirements-test.txt

# virtualenv of dpd

# inside dream:
# dreamtools new dist dream_weather -d dream \
  #  -s convers-evaluator-annotator \
  #  -s spacy-nounphrases \
  #  -s convers-evaluator-selector \
  #  -s dff-intent-responder-skill \
  #  -s intent-catcher \
  #  -s ner \
  #  -s entity-detection \
  #  -s dff-weather-skill \
  #  -s dialogpt \
  #  --compose-override --compose-dev --compose-proxy

# run tests