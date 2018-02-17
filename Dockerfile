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

EXPOSE 8000

CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:8000", "tesla_analytics.main:application"]
