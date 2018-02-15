FROM python:alpine

COPY . /app
WORKDIR /app
RUN apk update && apk upgrade && apk add --no-cache git \
    build-base \
    postgresql \
    postgresql-dev \
    libpq \
    libffi-dev
RUN pip install -r /app/requirements.txt
