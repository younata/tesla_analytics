FROM python:alpine

COPY . /app
WORKDIR /app
RUN apk update && apk upgrade && apk add --no-cache git
RUN pip install -r /app/requirements.txt
