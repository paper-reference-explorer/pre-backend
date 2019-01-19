This repository provides the backend for the paper-references-explorer website. 



## Setup
To run the setup in parallel, run:
```bash
sudo docker-compose -f docker-related/docker-compose.services.yml -f docker-related/docker-compose.setup.step1.yml build; sudo docker-compose -f docker-related/docker-compose.services.yml -f docker-related/docker-compose.setup.step2.yml build
sudo docker-compose -f docker-related/docker-compose.services.yml -f docker-related/docker-compose.setup.step1.yml up
sudo docker-compose -f docker-related/docker-compose.services.yml -f docker-related/docker-compose.setup.step2.yml up
```

To run the setup automatically, sequentially and with correct exit codes, run:
```bash
sudo docker-compose -f docker-related/docker-compose.services.yml -f docker-related/docker-compose.setup.step1.yml build
sudo docker-compose -f docker-related/docker-compose.services.yml -f docker-related/docker-compose.setup.step2.yml build
sudo docker-compose -f docker-related/docker-compose.services.yml -f docker-related/docker-compose.setup.step1.yml up --abort-on-container-exit --exit-code-from watcher-blast blast watcher-blast
sudo docker-compose -f docker-related/docker-compose.services.yml -f docker-related/docker-compose.setup.step1.yml up --abort-on-container-exit --exit-code-from watcher-postgres postgres watcher-postgres
sudo docker-compose -f docker-related/docker-compose.services.yml -f docker-related/docker-compose.setup.step1.yml up --abort-on-container-exit --exit-code-from watcher-redis redis watcher-redis
sudo docker-compose -f docker-related/docker-compose.services.yml -f docker-related/docker-compose.setup.step2.yml up --abort-on-container-exit --exit-code-from watcher-count-referenced-by postgres redis watcher-count-referenced-by
```

## Static
The data will be stored within the `mounts/` folder. The API can be summoned by calling
```bash
sudo docker-compose -f docker-related/docker-compose.api.yml up
```

## Development
After setting up the data, start the debug flask server with
```bash
sudo docker-compose -f docker-related/docker-compose.api.yml -f docker-related/docker-compose.api.dev.yml up
```