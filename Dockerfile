FROM python:3.7-alpine
RUN apk add git
RUN pip install pipenv
WORKDIR /usr/src/app

COPY Pipfile ./
COPY Pipfile.lock ./
RUN pipenv install --system --deploy --ignore-pipfile

COPY . .
CMD ["python", "./main.py"]
