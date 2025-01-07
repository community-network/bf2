FROM ubuntu:24.04

RUN apt-get update && apt-get install -y libssl-dev build-essential && apt-get clean

COPY ealist /ealist

WORKDIR /ealist

RUN make

RUN ./ealist