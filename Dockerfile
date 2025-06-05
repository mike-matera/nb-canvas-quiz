# 
# Build a Jupyter Stack specific for my Python for Everyone class. 
#
ARG PYTHON_VERSION=3.12
ARG DEBIAN_VERSION=slim-bookworm

FROM docker.io/python:${PYTHON_VERSION}-${DEBIAN_VERSION}

RUN apt update -y && apt install -y wget tree && apt clean -y

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

ARG NB_UID="1000"
ARG NB_USER="student" 

# Create the student user
ENV NB_UID=${NB_UID} \
    NB_USER=${NB_USER}
RUN useradd --no-log-init --create-home --shell /bin/bash --uid ${NB_UID} ${NB_USER}
USER ${NB_USER}

COPY --chown=${NB_UID}:${NB_UID} pyproject.toml README.md uv.lock /app/
COPY --chown=${NB_UID}:${NB_UID} src/ /app/src 
COPY --chown=${NB_UID}:${NB_UID} deps/ /app/deps 
WORKDIR /app 

# Install Python dependencies
RUN uv sync --locked

ENV PATH="/app/.venv/bin:$PATH" \
    PORT=32453 \
    NBQUIZ_TESTBANKS=/testbank/testbank.zip

CMD nbquiz server 
