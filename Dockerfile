FROM python:3.9.1

RUN pip install pipenv

COPY . /app

WORKDIR /app

ENV PYTHONPATH "${PYTHONPATH}:/app"

RUN pipenv install --system --deploy --ignore-pipfile
