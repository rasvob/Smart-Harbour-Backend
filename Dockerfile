FROM python:3.11-bookworm as builder

ENV DEBIAN_FRONTEND=noninteractive 
ENV PDM_CHECK_UPDATE=false

RUN mkdir -p /src/data
RUN mkdir -p /src/app
WORKDIR /src

# RUN apt-get update && apt-get install ffmpeg libsm6 libxext6 iputils-ping net-tools iproute2  -y
RUN pip install -U pip setuptools wheel
RUN pip install -U pdm

COPY pyproject.toml pdm.lock /src/
RUN pdm config python.use_venv False
RUN pdm install --check --prod --no-editable

FROM builder as development
COPY .env.docker /src/.env
EXPOSE 8010
CMD ["pdm", "run", "start-docker-dev"]

FROM builder as production
EXPOSE 443
COPY /app /src/app
COPY .env.docker /src/.env
CMD ["pdm", "run", "start-docker-prod"]