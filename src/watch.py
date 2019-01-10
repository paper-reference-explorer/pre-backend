import abc
import csv
import logging
import socket
import time
from pathlib import Path
from typing import List, Tuple

import click
import psycopg2
import redis
import requests

logging.basicConfig(format='%(asctime)s - %(levelname)-8s - %(name)s - %(message)s', level=logging.DEBUG)
logger = logging.getLogger(__name__)


@click.group()
def cli():
    pass


class Setup(abc.ABC):
    def __init__(self, host: str, port: int, file_glob: str):
        self._host = host
        self._port = port
        self._file_glob = file_glob
        self._input_path, self._input_file_paths = self._get_paths()
        self._wait_until_open()

    @property
    @abc.abstractmethod
    def _filename_skip_list(self) -> List[str]:
        pass

    @abc.abstractmethod
    def _step(self, file: Path) -> None:
        pass

    @abc.abstractmethod
    def _post_setup(self) -> None:
        pass

    def _get_paths(self) -> Tuple[Path, List[Path]]:
        base_path = Path('data')
        input_path = base_path / 'input'
        input_file_paths = input_path.glob(self._file_glob)
        input_file_paths = sorted(input_file_paths, reverse=True)
        return input_path, input_file_paths

    def _wait_until_open(self) -> None:
        start_time = time.time()
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        connection_info = (self._host, self._port)
        try:
            result = sock.connect_ex(connection_info)
        except socket.gaierror as error:
            if error.errno == -2:
                logger.error(f'Name or service "{self._host}" not known. Either the docker-compose file is wrong'
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
        logging.info(f'Time passed waiting: {duration:.02f}')

    def run(self) -> None:
        self._do_work()
        self._post_setup()

    def _do_work(self) -> None:
        for input_file_path in self._input_file_paths:
            start_time = time.time()

            if input_file_path.name in self._filename_skip_list:
                continue

            self._log_filename(input_file_path)
            self._step(input_file_path)

            end_time = time.time()
            duration = end_time - start_time
            logging.info(f'Time passed: {duration:.02f}')

    @staticmethod
    def _log_filename(filename: Path) -> None:
        logging.info(f'Reading {filename.name}...')


class SetupBlast(Setup):
    def __init__(self, host: str, port: int, file_glob: str):
        super().__init__(host, port, file_glob)

    @property
    def _filename_skip_list(self) -> List[str]:
        return []

    def _step(self, file: Path) -> None:
        response = requests.post(f'http://{self._host}:{self._port}/rest/_bulk', data=open(str(file), 'rb'))
        logger.info(f'{response.status_code}: {response.content}')

    def _post_setup(self) -> None:
        pass


class SetupRedis(Setup):
    def __init__(self, host: str, port: int, file_glob: str):
        super().__init__(host, port, file_glob)
        redis_db = 0
        self._connection = redis.Redis(host=self._host, port=self._port, db=redis_db)

    @property
    def _filename_skip_list(self) -> List[str]:
        return []

    def _step(self, file: Path) -> None:
        with open(str(file), newline='') as input_file:
            file_reader = csv.reader(input_file)
            for arxiv_id, year, authors, title in file_reader:
                data = {'year': year, 'authors': authors, 'title': title}
                self._connection.hmset(arxiv_id, data)

    def _post_setup(self) -> None:
        pass


class SetupPostgres(Setup):
    def __init__(self, host: str, port: int, file_glob: str):
        super().__init__(host, port, file_glob)
        self._connection = psycopg2.connect(f"host='{self._host}' port={self._port} dbname=postgres"
                                            + " user=postgres password=mysecretpassword")
        self._read_priority_files()

    @property
    def _filename_skip_list(self) -> List[str]:
        return ['create_tables.sql', 'insert_into_papers.sql']

    def _step(self, file: Path) -> None:
        cursor = self._connection.cursor()
        cursor.execute(open(str(file), 'r').read())
        self._connection.commit()
        cursor.close()

    def _post_setup(self) -> None:
        self._connection.close()

    def _read_priority_files(self) -> None:
        for input_file_name in self._filename_skip_list:
            input_file_path = self._input_path / input_file_name
            self._log_filename(input_file_path)
            cursor = self._connection.cursor()
            cursor.execute(open(str(input_file_path), 'r').read())
            self._connection.commit()
            cursor.close()


@cli.command()
@click.option('--host', '-h', type=str, default='blast', help='host to connect to')
@click.option('--port', '-p', type=int, default=10002, help='port to connect to')
@click.option('--file-glob', '-fg', type=str, default='*.json', help='files to search for')
def init_blast(host: str, port: int, file_glob: str) -> None:
    SetupBlast(host, port, file_glob).run()


@cli.command()
@click.option('--host', '-h', type=str, default='redis', help='host to connect to')
@click.option('--port', '-p', type=int, default=6379, help='port to connect to')
@click.option('--file-glob', '-fg', type=str, default='*.csv', help='files to search for')
def init_redis(host: str, port: int, file_glob: str) -> None:
    SetupRedis(host, port, file_glob).run()


@cli.command()
@click.option('--host', '-h', type=str, default='postgres', help='host to connect to')
@click.option('--port', '-p', type=int, default=5432, help='port to connect to')
@click.option('--file-glob', '-fg', type=str, default='*.sql', help='files to search for')
def init_postgres(host: str, port: int, file_glob: str) -> None:
    SetupPostgres(host, port, file_glob).run()


if __name__ == '__main__':
    cli()
