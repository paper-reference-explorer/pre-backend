FROM python:3.7-alpine as converter
RUN apk add git
RUN pip install pipenv
WORKDIR /usr/src/app
COPY Pipfile .
COPY Pipfile.lock .
RUN pipenv install --system --deploy --ignore-pipfile --dev
COPY data ./data
COPY convert.py .
RUN python ./convert.py

FROM python:3.7-alpine as py
RUN apk add git
RUN pip install pipenv
WORKDIR /usr/src/app
COPY Pipfile .
COPY Pipfile.lock .
RUN pipenv install --system --deploy --ignore-pipfile

FROM py as blast
COPY --from=converter /usr/src/app/data/output_for/blast ./data/input
COPY watch_blast.py .
CMD ["python", "./watch_blast.py"]

FROM py as redis
COPY --from=converter /usr/src/app/data/output_for/redis ./data/input
COPY watch_redis.py .
CMD ["python", "./watch_redis.py"]
