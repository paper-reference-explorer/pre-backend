.PHONY: dev fmt prod setup stats test

dev:
	sudo docker-compose -f docker-related/docker-compose.services.yml -f docker-related/docker-compose.api.yml -f docker-related/docker-compose.api.dev.yml build
	sudo docker-compose -f docker-related/docker-compose.services.yml -f docker-related/docker-compose.api.yml -f docker-related/docker-compose.api.dev.yml up

fmt:
# sorting imports
	isort -r src/* tests/*
# code formatter
	black --py36 --skip-string-normalization --diff src tests
# linting
	flake8 src tests

prod:
	sudo docker-compose -f docker-related/docker-compose.services.yml -f docker-related/docker-compose.api.yml build
	sudo docker-compose -f docker-related/docker-compose.services.yml -f docker-related/docker-compose.api.yml up

setup:
	sudo docker-compose -f docker-related/docker-compose.services.yml -f docker-related/docker-compose.setup.step1.yml build
	sudo docker-compose -f docker-related/docker-compose.services.yml -f docker-related/docker-compose.setup.step2.yml build
	sudo docker-compose -f docker-related/docker-compose.services.yml -f docker-related/docker-compose.setup.step1.yml up --abort-on-container-exit --exit-code-from watcher-postgres postgres watcher-postgres
	sudo docker-compose -f docker-related/docker-compose.services.yml -f docker-related/docker-compose.setup.step1.yml up --abort-on-container-exit --exit-code-from watcher-redis redis watcher-redis
	sudo docker-compose -f docker-related/docker-compose.services.yml -f docker-related/docker-compose.setup.step1.yml up --abort-on-container-exit --exit-code-from watcher-blast blast watcher-blast
	sudo docker-compose -f docker-related/docker-compose.services.yml -f docker-related/docker-compose.setup.step2.yml up --abort-on-container-exit --exit-code-from watcher-count-referenced-by postgres redis watcher-count-referenced-by

stats:
# same as radon commands but actually fails if conditions are not met
	xenon --max-absolute C --max-modules A --max-average A src
	xenon --max-absolute C --max-modules A --max-average A tests
# minimal code statistics
	radon cc --min B src tests
	radon mi --min B src tests
# security
	bandit -r src

test:
# tests and coverage
	python -m pytest --cov=src --cov-fail-under=4 tests