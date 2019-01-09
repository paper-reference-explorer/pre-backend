FROM python:3.7-alpine as converter
RUN apk add git
RUN pip install pipenv
WORKDIR /usr/src/app

COPY Pipfile ./
COPY Pipfile.lock ./
RUN pipenv install --system --deploy --ignore-pipfile --dev

COPY data .
COPY convert.py .
RUN python ./convert.py


FROM python:3.7-alpine
RUN apk add git
RUN pip install pipenv
WORKDIR /usr/src/app

COPY Pipfile ./
COPY Pipfile.lock ./
RUN pipenv install --system --deploy --ignore-pipfile

COPY --from=converter /usr/src/app/data/output ./data/input

COPY watch.py .
CMD ["python", "./watch.py"]
