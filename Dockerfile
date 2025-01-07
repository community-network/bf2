FROM ubuntu:24.04 AS build-stage

RUN apt-get update && apt-get install -y libgeoip-dev libmysqlclient-dev build-essential && apt-get clean

COPY gslist /gslist

WORKDIR /gslist

RUN make

FROM --platform=$BUILDPLATFORM python:3.12 AS requirements-stage
WORKDIR /tmp

RUN pip install poetry poetry-plugin-export
COPY ./bf2-worker/pyproject.toml ./poetry.lock* /tmp/
RUN poetry export -f requirements.txt --output requirements.txt --without-hashes

FROM ubuntu:24.04

# AMD64 build for bfbc2
# RUN apt-get install -y wget software-properties-common gnupg2 xvfb
# RUN dpkg --add-architecture i386
# RUN mkdir -pm755 /etc/apt/keyrings
# RUN wget -O /etc/apt/keyrings/winehq-archive.key https://dl.winehq.org/wine-builds/winehq.key
# RUN wget -NP /etc/apt/sources.list.d/ https://dl.winehq.org/wine-builds/ubuntu/dists/lunar/winehq-lunar.sources
# RUN apt-get update
# RUN apt-get install --no-install-recommends -y winehq-stable winetricks winbind

# ARM build for bfbc2
# WORKDIR /temp
# ADD https://github.com/AndreRH/hangover/releases/download/hangover-9.3/hangover_9.3_ubuntu2310_mantic_arm64.tar /temp
# RUN tar -xvf hangover_9.3_ubuntu2310_mantic_arm64.tar
# RUN apt-get update && apt-get install -y ./hangover-wine_9.3~mantic_arm64.deb

RUN apt-get update && apt-get install -y python3 curl python3-pip python3-venv python-is-python3 && apt-get clean
# ENV WINEDEBUG=fixme-all
# ENV DISPLAY :0

# Set pip env
RUN python3 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY --from=requirements-stage /tmp/requirements.txt /code/requirements.txt
RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt

COPY ./bf2-worker /bf2-api
COPY ./ealist /bf2-api/ealist
COPY --from=build-stage /gslist/gslist /bf2-api/gslist-2
WORKDIR /bf2-api

ENTRYPOINT [ "python3.12", "serverList.py" ]