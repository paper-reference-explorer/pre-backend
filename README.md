This repository provides the backend for the paper-references-explorer website. 
It offers two basic functionalities: 
search for a paper and generation of the graph data for a set of papers.

To setup the data, execute the commands individually. Once the watcher exits, exit the command
and run the next one.
```bash
sudo docker-compose -f docker-related/docker-compose.redis.yml up
sudo docker-compose -f docker-related/docker-compose.postgres.yml up
sudo docker-compose -f docker-related/docker-compose.blast.yml up
```

The data will be stored within the `mounts/` folder. The API can be summoned by calling
```bash
sudo docker-compose -f docker-related/docker-compose.api.yml up
```