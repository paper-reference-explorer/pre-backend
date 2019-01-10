from pathlib import Path
import logging
import time

import psycopg2

from watch_helper import wait_until_open

logging.basicConfig(format='%(asctime)s - %(levelname)-8s - %(name)s - %(message)s', level=logging.DEBUG)
logger = logging.getLogger(__name__)


def main(host: str = 'postgres', port: int = 5432, file_glob: str = '*.sql') -> None:
    wait_until_open(host, port)
    base_path = Path('data')
    input_path = base_path / 'input'
    input_file_paths = input_path.glob(file_glob)
    input_file_paths = sorted(input_file_paths, reverse=False)

    connection = psycopg2.connect(f"host='{host}' port={port} dbname=postgres user=postgres password=mysecretpassword")

    important_files = ['create_tables.sql', 'insert_into_papers.sql']
    for input_file_name in important_files:
        input_file_path = input_path / input_file_name
        logging.info(f'Reading {input_file_path.name}...')
        cursor = connection.cursor()
        cursor.execute(open(str(input_file_path), 'r').read())
        connection.commit()
        cursor.close()

    for input_file_path in input_file_paths:
        start_time = time.time()

        if input_file_path.name in important_files:
            continue

        logging.info(f'Reading {input_file_path.name}...')
        cursor = connection.cursor()
        cursor.execute(open(str(input_file_path), 'r').read())
        connection.commit()
        cursor.close()

        end_time = time.time()
        duration = end_time - start_time
        logging.info(f'Time passed: {duration:.02f}')

    connection.close()


if __name__ == '__main__':
    main()
