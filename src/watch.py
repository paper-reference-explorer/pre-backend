import abc
import csv
import logging
import socket
import time
from pathlib import Path
from typing import List, Tuple

import click
import requests

import config

logging.basicConfig(format=config.LOG_FORMAT, level=logging.DEBUG)
logger = logging.getLogger(__name__)


@click.group()
def cli():
    pass


class Setup(abc.ABC):
    def __init__(self):
        # self._service_config must be set by the implementation class
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
        input_path = base_path / 'output_for' / self._service_config.FOLDER_NAME
        input_file_paths = input_path.glob(self._service_config.FILE_GLOB)
        input_file_paths = sorted(input_file_paths, reverse=True)
        return input_path, input_file_paths

    def _wait_until_open(self) -> None:
        start_time = time.time()
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        connection_info = (self._service_config.HOST, self._service_config.PORT)
        try:
            result = sock.connect_ex(connection_info)
        except socket.gaierror as error:
            if error.errno == -2:
                logger.error(f'Name or service "{self._service_config.HOST}" not known.'
                             f' Either the docker-compose file is wrong or this file is run outside of docker.')
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
    def __init__(self):
        # set it here so the type is correctly recognized
        self._service_config = config.BlastServiceConfig
        super().__init__()

    @property
    def _filename_skip_list(self) -> List[str]:
        return []

    def _step(self, file: Path) -> None:
        response = requests.post(self._service_config.POST_URL, data=open(str(file), 'rb'))
        logger.info(f'{response.status_code}: {response.content}')

    def _post_setup(self) -> None:
        pass


class SetupPostgres(Setup):
    def __init__(self):
        # set it here so the type is correctly recognized
        self._service_config = config.PostgresServiceConfig
        super().__init__()
        self._connection = self._service_config.create_connection()
        self._read_priority_files()

    @property
    def _filename_skip_list(self) -> List[str]:
        return [self._service_config.CREATE_TABLE_FILE_NAME, self._service_config.INSERT_INTO_PAPERS_FILE_NAME]

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


class SetupRedis(Setup):
    def __init__(self):
        # set it here so the type is correctly recognized
        self._service_config = config.RedisServiceConfig
        super().__init__()
        self._connection = self._service_config.create_connection()

    @property
    def _filename_skip_list(self) -> List[str]:
        return []

    def _step(self, file: Path) -> None:
        with open(str(file), newline='') as input_file:
            file_reader = csv.reader(input_file)
            for paper_id, year, authors, title in file_reader:
                data = {'year': year, 'authors': authors, 'title': title}
                self._connection.hmset(paper_id, data)

    def _post_setup(self) -> None:
        pass


@cli.command()
def init_blast() -> None:
    SetupBlast().run()


@cli.command()
def init_postgres() -> None:
    SetupPostgres().run()


@cli.command()
def init_redis() -> None:
    SetupRedis().run()


@cli.command()
def count_referenced_by() -> None:
    postgres_service_config = config.PostgresServiceConfig
    postgres_connection = postgres_service_config.create_connection()

    sql = """
SELECT p.ID, COUNT(*)  
FROM papers p
    INNER JOIN refs r 
        ON r.referencee = p.ID
GROUP BY p.ID"""
    cursor = postgres_connection.cursor()
    cursor.execute(sql)

    redis_service_config = config.RedisServiceConfig
    redis_connection = redis_service_config.create_connection()
    for paper_id, referenced_count in cursor:
        redis_connection.hsetnx(paper_id, 'referenced_by_n', referenced_count)
    postgres_connection.commit()
    cursor.close()

    postgres_connection.close()


if __name__ == '__main__':
    cli()
