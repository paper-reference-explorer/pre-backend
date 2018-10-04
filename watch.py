from pathlib import Path
import logging
import socket
import time

import requests

logging.basicConfig(format='%(asctime)s - %(levelname)-8s - %(name)s - %(message)s', level=logging.DEBUG)
logger = logging.getLogger(__name__)


def main() -> None:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    connection_info = ('search', 10002)
    result = sock.connect_ex(connection_info)
    while result != 0:
        logger.info("Port is not open")
        time.sleep(1)
        result = sock.connect_ex(connection_info)

    logger.info("Port is open")
    base_path = Path('data')
    input_path = base_path / 'output'

    input_file_paths = input_path.glob('*.json')
    input_file_paths = sorted(input_file_paths, reverse=True)
    for input_file_path in input_file_paths:
        logging.info(f'Reading {input_file_path.name}...')
        response = requests.post(f'http://{connection_info[0]}:{connection_info[1]}/rest/_bulk',
                                 data=open(str(input_file_path), 'rb'))
        logger.info(f'{response.status_code}: {response.content}')


if __name__ == '__main__':
    main()
