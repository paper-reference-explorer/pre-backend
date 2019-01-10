import csv
import logging
import socket
import time
from pathlib import Path

import click
import psycopg2
import redis
import requests

logging.basicConfig(format='%(asctime)s - %(levelname)-8s - %(name)s - %(message)s', level=logging.DEBUG)
logger = logging.getLogger(__name__)


@click.group()
def cli():
    pass


@cli.command()
@click.option('--host', '-h', type=str, default='blast', help='host to connect to')
@click.option('--port', '-p', type=int, default=10002, help='port to connect to')
@click.option('--file-glob', '-fg', type=str, default='*.json', help='files to search for')
def init_blast(host: str, port: int, file_glob: str) -> None:
    _wait_until_open(host, port)
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


@cli.command()
@click.option('--host', '-h', type=str, default='redis', help='host to connect to')
@click.option('--port', '-p', type=int, default=6379, help='port to connect to')
@click.option('--file-glob', '-fg', type=str, default='*.csv', help='files to search for')
def init_redis(host: str, port: int, file_glob: str) -> None:
    _wait_until_open(host, port)
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


@cli.command()
@click.option('--host', '-h', type=str, default='postgres', help='host to connect to')
@click.option('--port', '-p', type=int, default=5432, help='port to connect to')
@click.option('--file-glob', '-fg', type=str, default='*.sql', help='files to search for')
def init_postgres(host: str, port: int, file_glob: str) -> None:
    _wait_until_open(host, port)
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


def _wait_until_open(host: str, port: int) -> None:
    start_time = time.time()
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    connection_info = (host, port)
    try:
        result = sock.connect_ex(connection_info)
    except socket.gaierror as error:
        if error.errno == -2:
            logger.error(f'Name or service "{host}" not known. Either the docker-compose file is wrong'
                         + ' or this file is run outside of docker.')
            exit(-2)
        else:
            raise error

    while result != 0:
        logger.info('Port is not open')
        time.sleep(1)
        result = sock.connect_ex(connection_info)

    logger.info('Port is open')
    for _ in range(5):
        logger.info('.')
        time.sleep(1)

    end_time = time.time()
    duration = end_time - start_time
    logging.info(f'Time passed: {duration:.02f}')


if __name__ == '__main__':
    cli()
