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

prod:
	sudo docker-compose -f docker-related/docker-compose.services.yml -f docker-related/docker-compose.api.yml build
	sudo docker-compose -f docker-related/docker-compose.services.yml -f docker-related/docker-compose.api.yml up
