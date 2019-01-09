from pathlib import Path
import logging
import time

import requests

from watch_helper import wait_until_open

logging.basicConfig(format='%(asctime)s - %(levelname)-8s - %(name)s - %(message)s', level=logging.DEBUG)
logger = logging.getLogger(__name__)


def main(host: str = 'blast', port: int = 10002, file_glob: str = '*.json') -> None:
    wait_until_open(host, port)
    base_path = Path('data')
    input_path = base_path / 'input'

    input_file_paths = input_path.glob(file_glob)
    input_file_paths = sorted(input_file_paths, reverse=False)

    for input_file_path in input_file_paths:
        start_time = time.time()

        logging.info(f'Reading {input_file_path.name}...')
        response = requests.post(f'http://{host}:{port}/rest/_bulk', data=open(str(input_file_path), 'rb'))
        logger.info(f'{response.status_code}: {response.content}')

        end_time = time.time()
        duration = end_time - start_time
        logging.info(f'Time passed: {duration:.02f}')


if __name__ == '__main__':
    main()
