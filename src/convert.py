import abc
import csv
import logging
import shutil
from pathlib import Path
from typing import TextIO, Optional, List

import click
from git import Repo

import config
import processing

logging.basicConfig(format=config.LOG_FORMAT, level=logging.DEBUG)
logger = logging.getLogger(__name__)

id_index = 0
references_index = 4
authors_index = 5
title_index = 6


class Converter(abc.ABC):
    def __init__(self, output_path: Path, clean_folder: bool):
        super().__init__()
        # self._service_config must be set by the implementation class
        self.output_path = output_path / self._service_config.FOLDER_NAME
        clean_folder_maybe(self.output_path, clean_folder)
        self._file_index = None  # type: int
        self._current_year = None  # type: str
        self._n_elements_in_file = None  # type: int
        self._max_elements_in_file = 10000
        self._is_first_line = None  # type: bool

    def input_file_opened(self, year: str) -> None:
        self._file_index = 1
        self._n_elements_in_file = 0
        self._current_year = year
        self._open_output_file()

    @property
    def _output_file_path(self) -> str:
        return str(self.output_path / f'{self._current_year}_{self._file_index}.{self._service_config.FILE_EXTENSION}')

    @abc.abstractmethod
    def _open_output_file(self) -> None:
        pass

    def handle_line(self, fields: List[str]) -> None:
        self._n_elements_in_file += 1
        if self._n_elements_in_file >= self._max_elements_in_file:
            self._close_output_file()
            self._n_elements_in_file = 0
            self._file_index += 1
            self._open_output_file()

        self._handle_fields(fields)

    @abc.abstractmethod
    def _handle_fields(self, fields: List[str]) -> None:
        pass

    def input_file_closed(self) -> None:
        self._close_file()

    def _close_output_file(self) -> None:
        self._close_file()

    @abc.abstractmethod
    def _close_file(self) -> None:
        pass

    @abc.abstractmethod
    def post_conversion(self) -> None:
        pass


class BlastConverter(Converter):
    def __init__(self, output_path_base: Path, clean_folder: bool):
        # set it here so the type is correctly recognized
        self._service_config = config.BlastServiceConfig
        super().__init__(output_path_base, clean_folder)
        self._current_file = None  # type: TextIO

    def _open_output_file(self) -> None:
        self._is_first_line = True
        self._current_file = open(self._output_file_path, 'w')
        self._current_file.write(self._service_config.FILE_START)

    def _handle_fields(self, fields: List[str]) -> None:
        document = self._convert_to_document(fields)
        self._current_file.write(document)
        self._is_first_line = False

    def _convert_to_document(self, fields: List[str]) -> str:
        arxiv_id = processing.clean_id(fields[id_index])
        authors = processing.clean_authors(fields[authors_index])
        title = processing.clean_title(fields[title_index])
        document = self._service_config.FILE_ENTRY(self._is_first_line, arxiv_id, self._current_year, authors, title)
        return document

    def _close_file(self) -> None:
        if self._current_file is not None and not self._current_file.closed:
            self._current_file.write(self._service_config.FILE_END)
            self._current_file.close()

    def post_conversion(self) -> None:
        pass


class PostgresConverter(Converter):
    def __init__(self, output_path_base: Path, clean_folder: bool):
        # set it here so the type is correctly recognized
        self._service_config = config.PostgresServiceConfig
        super().__init__(output_path_base, clean_folder)
        self._current_file = None  # type: TextIO
        self._ids = set()

    def _open_output_file(self) -> None:
        self._is_first_line = True
        self._current_file = open(self._output_file_path, 'w')
        self._current_file.write(self._service_config.INSERT_INTO_REFS_START)

    def _handle_fields(self, fields: List[str]) -> None:
        document = self._convert_to_document(fields)
        if document is not None:
            self._current_file.write(document)
            self._is_first_line = False

    def _convert_to_document(self, fields: List[str]) -> Optional[str]:
        arxiv_id = processing.clean_id(fields[id_index])
        refs = fields[references_index].split(',')
        refs = [processing.clean_id(r) for r in refs]
        if len(refs) == 1 and refs[0] == '':
            return None

        self._ids.add(arxiv_id)
        [self._ids.add(r) for r in refs]
        document = self._service_config.INSERT_INTO_REFS_ENTRY(self._is_first_line, arxiv_id, refs)
        return document

    def _close_file(self) -> None:
        self._current_file.write(self._service_config.INSERT_INTO_REFS_END)
        self._current_file.close()

    def post_conversion(self) -> None:
        create_tables_file_path = self.output_path / self._service_config.CREATE_TABLE_FILE_NAME
        with open(str(create_tables_file_path), 'w') as create_tables_file:
            create_tables_file.write(config.PostgresServiceConfig.CREATE_TABLES_SQL)

        insert_into_papers_file_path = self.output_path / self._service_config.INSERT_INTO_PAPERS_FILE_NAME
        with open(str(insert_into_papers_file_path), 'w') as insert_into_papers_file:
            document = config.PostgresServiceConfig.INSERT_INTO_PAPERS_SQL(self._ids)
            insert_into_papers_file.write(document)


class RedisConverter(Converter):
    def __init__(self, output_path_base: Path, clean_folder: bool):
        # set it here so the type is correctly recognized
        self._service_config = config.RedisServiceConfig
        super().__init__(output_path_base, clean_folder)
        self._writer = None  # type: csv.writer

    def _open_output_file(self) -> None:
        self._is_first_line = True
        output_file = open(self._output_file_path, 'w', newline='')
        self._writer = csv.writer(output_file)

    def _handle_fields(self, fields: List[str]) -> None:
        document = self._convert_to_document(fields)
        self._writer.writerow(document)
        self._is_first_line = False

    def _convert_to_document(self, fields: List[str]) -> List[str]:
        arxiv_id = processing.clean_id(fields[id_index])
        authors = processing.clean_field(fields[authors_index]).replace(',', ', ')
        title = processing.clean_field(fields[title_index])
        document = [arxiv_id, self._current_year, authors, title]
        return document

    def _close_file(self) -> None:
        pass

    def post_conversion(self) -> None:
        pass


def clean_folder_maybe(path: Path, clean_folder: bool, recreate: bool = True) -> None:
    if clean_folder and path.exists():
        logger.info(f'Cleaning folder {path.name}')
        shutil.rmtree(path)

    if recreate:
        path.mkdir(exist_ok=True, parents=True)


# only blast makes sense to cache
@click.command()
def main(source_url: str = 'https://github.com/paperscape/paperscape-data.git',
         n_max_splits: int = 7, max_elements_per_file: int = 10000, max_n_files: Optional[int] = 2,
         clean_input: bool = False, clean_output_for_blast: bool = False, clean_output_for_redis: bool = False,
         clean_output_for_postgres: bool = False) -> None:
    base_path = Path('data')
    input_path = base_path / 'input'
    clean_folder_maybe(input_path, clean_input, recreate=False)
    clone_repo(input_path, source_url)

    output_path_base = base_path / 'output_for'
    converters = [
        BlastConverter(output_path_base, clean_output_for_blast),
        RedisConverter(output_path_base, clean_output_for_redis),
        PostgresConverter(output_path_base, clean_output_for_postgres)
    ]

    n_total_elements = 0
    input_file_paths = input_path.glob('*.csv')
    input_file_paths = sorted(input_file_paths, reverse=False)
    for index, input_file_path in enumerate(input_file_paths):
        if max_n_files is not None and index >= max_n_files:
            break

        logging.info(f'Converting {input_file_path.name}...')
        year = input_file_path.name[5:9]
        with open(str(input_file_path), 'r') as input_file:
            n_elements_in_file = 0

            [c.input_file_opened(year) for c in converters]

            for line in input_file:
                line_clean = line.strip()
                if line_clean.startswith('#'):
                    continue

                n_elements_in_file += 1
                fields = line.split(';', n_max_splits)
                [c.handle_line(fields) for c in converters]

            [c.input_file_closed() for c in converters]

            logging.info(f'N elements converted: {n_elements_in_file}')
            n_total_elements += n_elements_in_file

    [c.post_conversion() for c in converters]
    logging.info(f'N elements converted in total: {n_total_elements}')


def clone_repo(input_path, source_url):
    if not input_path.exists():
        logger.info('Cloning repo...')
        Repo.clone_from(source_url, input_path)
        logger.info('Finished cloning repo')


if __name__ == '__main__':
    main()
