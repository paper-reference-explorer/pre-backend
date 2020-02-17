SRC_FOLDER := src
TESTS_FOLDER := tests
PYTHON_FOLDERS := $(SRC_FOLDER) $(TESTS_FOLDER)
.PHONY: dev
dev:
	sudo docker-compose -f docker-related/docker-compose.services.yml -f docker-related/docker-compose.api.yml -f docker-related/docker-compose.api.dev.yml build
	sudo docker-compose -f docker-related/docker-compose.services.yml -f docker-related/docker-compose.api.yml -f docker-related/docker-compose.api.dev.yml up

.PHONY: fmt
fmt:
	# sorting imports
	pipenv run isort -rc $(PYTHON_FOLDERS)
	# code formatter
	pipenv run black $(PYTHON_FOLDERS)
	# linting
	pipenv run flake8 $(PYTHON_FOLDERS)

.PHONY: prod
prod:
	sudo docker-compose -f docker-related/docker-compose.services.yml -f docker-related/docker-compose.api.yml build
	sudo docker-compose -f docker-related/docker-compose.services.yml -f docker-related/docker-compose.api.yml up

.PHONY: setup
setup:
	sudo docker-compose -f docker-related/docker-compose.services.yml -f docker-related/docker-compose.setup.step1.yml build
	sudo docker-compose -f docker-related/docker-compose.services.yml -f docker-related/docker-compose.setup.step2.yml build
	sudo docker-compose -f docker-related/docker-compose.services.yml -f docker-related/docker-compose.setup.step1.yml up --abort-on-container-exit --exit-code-from watcher-postgres postgres watcher-postgres
	sudo docker-compose -f docker-related/docker-compose.services.yml -f docker-related/docker-compose.setup.step1.yml up --abort-on-container-exit --exit-code-from watcher-redis redis watcher-redis
	sudo docker-compose -f docker-related/docker-compose.services.yml -f docker-related/docker-compose.setup.step1.yml up --abort-on-container-exit --exit-code-from watcher-blast blast watcher-blast
	sudo docker-compose -f docker-related/docker-compose.services.yml -f docker-related/docker-compose.setup.step2.yml up --abort-on-container-exit --exit-code-from watcher-count-referenced-by postgres redis watcher-count-referenced-by

.PHONY: stats
stats:
	# same as radon commands but actually fails if conditions are not met
	pipenv run xenon --max-absolute C --max-modules A --max-average A $(PYTHON_FOLDERS)
	# prints minimal code statistics
	pipenv run radon cc --min B $(PYTHON_FOLDERS)
	pipenv run radon mi --min B $(PYTHON_FOLDERS)
	# security
	pipenv run bandit -r $(SRC_FOLDER)

.PHONY: test
test:
	# tests and coverage
	pipenv run python -m pytest --cov=src --cov-fail-under=4 $(TESTS_FOLDER)
