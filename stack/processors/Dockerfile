FROM python:3.11.4 AS builder
COPY requirements.txt .
RUN pip install -r requirements.txt

FROM builder AS executor
WORKDIR /processors
COPY . /processors

CMD ["python", "./processor.py"]