FROM python:3.10.5-slim

# Cloning repos
RUN apt-get update && apt-get install -y --no-install-recommends git
RUN git clone https://github.com/deeppavlov/dream.git

#   Setting up virtual environment:
#1. For the project
COPY requirements.txt /src/requirements.txt
RUN pip install --no-cache-dir -r /src/requirements.txt
#2. For the test system
COPY deeppavlov_dreamtools/tests/requirements-test.txt /src/requirements-test.txt
RUN pip install --no-cache-dir -r /src/requirements-test.txt

COPY . /src/

WORKDIR /src/deeppavlov_dreamtools/tests
# run tests
CMD ["pytest", "--cov-config=.coveragerc", "--cov=deeppavlov_dreamtools", "."]
