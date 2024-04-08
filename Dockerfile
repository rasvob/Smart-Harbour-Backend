FROM python:3.11-bookworm as builder

ENV DEBIAN_FRONTEND=noninteractive 
ENV PDM_CHECK_UPDATE=false

RUN mkdir -p /src/data
RUN mkdir -p /src/app
RUN mkdir -p /src/certs
WORKDIR /src

# RUN apt-get update && apt-get install ffmpeg libsm6 libxext6 iputils-ping net-tools iproute2  -y
RUN pip install -U pip setuptools wheel
RUN pip install -U pdm

COPY pyproject.toml pdm.lock /src/
RUN pdm config python.use_venv False
RUN pdm install --check --prod --no-editable

COPY .env.docker /src/.env
COPY /certs /src/certs
ENV PYTHONPATH=/src/app

FROM builder as development
EXPOSE 8010
CMD ["pdm", "run", "start-docker-dev"]

FROM builder as production
EXPOSE 8010
COPY /app /src/app
COPY .env.docker /src/.env
CMD ["pdm", "run", "start-docker-prod"]