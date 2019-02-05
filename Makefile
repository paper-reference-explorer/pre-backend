.PHONY: test setup dev prod
dev:
	sudo docker-compose -f docker-related/docker-compose.services.yml -f docker-related/docker-compose.api.yml -f docker-related/docker-compose.api.dev.yml build
	sudo docker-compose -f docker-related/docker-compose.services.yml -f docker-related/docker-compose.api.yml -f docker-related/docker-compose.api.dev.yml up

fmt:
# sorting imports
	isort -r src/* tests/*
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

dev:
	sudo docker-compose -f docker-related/docker-compose.services.yml -f docker-related/docker-compose.api.yml -f docker-related/docker-compose.api.dev.yml build
	sudo docker-compose -f docker-related/docker-compose.services.yml -f docker-related/docker-compose.api.yml -f docker-related/docker-compose.api.dev.yml up

test:
# tests and coverage
	python -m pytest --cov=src --cov-fail-under=4 tests