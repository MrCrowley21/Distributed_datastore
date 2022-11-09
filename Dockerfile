FROM python:3.7

WORKDIR /Distributed_database

COPY requirements.txt requirements.txt

RUN pip install -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["python", "server.py"]