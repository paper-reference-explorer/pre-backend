from pathlib import Path
import logging
import time
import csv

import redis

from watch_helper import wait_until_open

logging.basicConfig(format='%(asctime)s - %(levelname)-8s - %(name)s - %(message)s', level=logging.DEBUG)
logger = logging.getLogger(__name__)


def main(host: str = 'redis', port: int = 6379, file_glob: str = '*.csv') -> None:
    wait_until_open(host, port)
    base_path = Path('data')
    input_path = base_path / 'input'
    input_file_paths = input_path.glob(file_glob)
    input_file_paths = sorted(input_file_paths, reverse=False)

    connection = redis.Redis(host=host, port=port, db=0)

    for input_file_path in input_file_paths:
        start_time = time.time()

        logging.info(f'Reading {input_file_path.name}...')
        with open(str(input_file_path), newline='') as input_file:
            file_reader = csv.reader(input_file)
            for arxiv_id, year, authors, title in file_reader:
                data = {'year': year, 'authors': authors, 'title': title}
                connection.hmset(arxiv_id, data)

        end_time = time.time()
        duration = end_time - start_time
        logging.info(f'Time passed: {duration:.02f}')


if __name__ == '__main__':
    main()
