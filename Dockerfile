FROM python:3.7-alpine as base
RUN apk add --no-cache git libpq
RUN apk add --virtual build-deps gcc python3-dev musl-dev postgresql-dev
RUN pip install pipenv
WORKDIR /usr/src/app
COPY Pipfile .
COPY Pipfile.lock .
RUN pipenv install --system --deploy --ignore-pipfile
RUN apk del build-deps

FROM base as converter
COPY data ./data
COPY convert.py .
RUN python ./convert.py

FROM base as py
COPY watch_helper.py .

FROM py as blast
COPY --from=converter /usr/src/app/data/output_for/blast ./data/input
COPY watch_blast.py .
CMD ["python", "./watch_blast.py"]

FROM py as redis
COPY --from=converter /usr/src/app/data/output_for/redis ./data/input
COPY watch_redis.py .
CMD ["python", "./watch_redis.py"]

FROM py as postgres
COPY --from=converter /usr/src/app/data/output_for/postgres ./data/input
COPY watch_postgres.py .
CMD ["python", "./watch_postgres.py"]
