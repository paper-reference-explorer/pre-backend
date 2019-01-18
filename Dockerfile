FROM python:3.7-alpine as base
RUN apk add --no-cache git libpq
RUN apk add --virtual build-deps gcc python3-dev musl-dev postgresql-dev
RUN pip install pipenv
WORKDIR /usr/src/app
COPY ./Pipfile .
COPY ./Pipfile.lock .
RUN pipenv install --system --deploy --ignore-pipfile
RUN apk del build-deps
RUN python -c "import nltk; nltk.download('stopwords')"
COPY ./src/ ./src/

FROM base as converter
COPY ./data ./data
RUN python ./src/convert.py

FROM base as blast
COPY --from=converter /usr/src/app/data/output_for/blast ./data/input
CMD ["python", "./src/watch.py", "init-blast"]

FROM base as redis
COPY --from=converter /usr/src/app/data/output_for/redis ./data/input
CMD ["python", "./src/watch.py", "init-redis"]

FROM base as postgres
COPY --from=converter /usr/src/app/data/output_for/postgres ./data/input
CMD ["python", "./src/watch.py", "init-postgres"]

FROM base as api
CMD ["python", "./src/api.py"]