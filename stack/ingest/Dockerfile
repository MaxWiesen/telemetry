FROM python:3.11.4 AS builder
COPY requirements.txt .
RUN pip install -r requirements.txt

FROM builder AS executor
WORKDIR /ingest
COPY . /ingest

CMD ["python", "./mqtt_handler.py"]