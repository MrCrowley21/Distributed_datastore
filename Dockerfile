FROM python:3.7

RUN mkdir /Distributed_database

ARG config config

COPY requirements.txt requirements.txt

COPY . /Distributed_database

COPY ${config} /Distributed_database/config

RUN pip install -r requirements.txt

WORKDIR /Distributed_database


CMD ["python", "server.py"]