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

FROM base as converter
COPY ./data ./data
COPY ./src/convert.py ./src/
RUN python ./src/convert.py

FROM base as py
COPY ./src/watch.py ./src/

FROM py as blast
COPY --from=converter /usr/src/app/data/output_for/blast ./data/input
CMD ["python", "./src/watch.py", "init-blast"]

FROM py as redis
COPY --from=converter /usr/src/app/data/output_for/redis ./data/input
CMD ["python", "./src/watch.py", "init-redis"]

FROM py as postgres
COPY --from=converter /usr/src/app/data/output_for/postgres ./data/input
CMD ["python", "./src/watch.py", "init-postgres"]

FROM base as api
COPY ./src/api.py ./src/
CMD ["python", "./src/api.py"]