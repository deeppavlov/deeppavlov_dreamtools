FROM python:3.10.5-slim

WORKDIR /usr/src/app

# Cloning repos
RUN apt-get update && apt-get install -y --no-install-recommends git
RUN git clone https://github.com/deeppavlovteam/dream.git
RUN git clone https://github.com/deeppavlovteam/deeppavlov_dreamtools.git

# Copy ground-truth files to container
COPY ./../static/dream_weather_dist_configs/ /usr/src/app/deeppavlov_dreamtools/deeppavlov_dreamtools/static/dream_weather_dist_configs

# Setting up virtual environment:
#1. For the project
WORKDIR /usr/src/app/deeppavlov_dreamtools
RUN pip install --no-cache-dir -r requirements.txt
#2. For the test system
WORKDIR /usr/src/app/deeppavlov_dreamtools/deeppavlov_dreamtools/tests
COPY ./tests/__init__.py ./tests/requirements-test.txt ./tests/test_distweather.py ./
RUN pip install --no-cache-dir -r requirements-test.txt
#3. Activation of the venv (1)
WORKDIR /usr/src/app/deeppavlov_dreamtools
RUN pip install -e ./
RUN virtualenv venv
ENV PATH="/venv/bin:$PATH"

# installing weather_distribution
WORKDIR /usr/src/app/dream/
RUN dreamtools new dist dream_weather -d dream -s convers-evaluator-annotator -s spacy-nounphrases -s \
convers-evaluator-selector -s dff-intent-responder-skill -s intent-catcher  -s ner -s entity-detection -s \
dff-weather-skill -s dialogpt  --compose-override --compose-dev --compose-proxy

# run tests
WORKDIR /usr/src/app/deeppavlov_dreamtools/deeppavlov_dreamtools/tests
RUN pytest -v test_distweather.py
