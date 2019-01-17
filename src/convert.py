import abc
import csv
import logging
import re
import shutil
from pathlib import Path
from typing import TextIO, Optional, List

import click
import nltk
from git import Repo

logging.basicConfig(format='%(asctime)s - %(levelname)-8s - %(name)s    - %(message)s', level=logging.DEBUG)
logger = logging.getLogger(__name__)

id_index = 0
references_index = 4
authors_index = 5
title_index = 6
min_title_word_length = 3

pattern_alpha = re.compile('[^a-zA-Z ]+')
pattern_alphanumeric = re.compile('[\W]+')
stop_words = set(nltk.corpus.stopwords.words('english'))
stemmer = nltk.stem.SnowballStemmer('english')
vocab = set()


class Converter(abc.ABC):

    def __init__(self, output_path: Path, clean_folder: bool, folder_name: str):
        super().__init__()
        self.output_path = output_path / folder_name
        clean_folder_maybe(self.output_path, clean_folder)

    @property
    @abc.abstractmethod
    def _output_extension(self) -> str:
        pass

    @abc.abstractmethod
    def open_input_file(self, year: str) -> None:
        pass

    @abc.abstractmethod
    def handle_line(self, line: str) -> None:
        pass

    @abc.abstractmethod
    def close_input_file(self) -> None:
        pass

    @abc.abstractmethod
    def post_conversion(self) -> None:
        pass


class BlastConverter(Converter):
    def __init__(self, output_path_base: Path, clean_folder: bool):
        super().__init__(output_path_base, clean_folder, 'blast')
        self._file_index = None  # type: int
        self._current_file = None  # type: TextIO
        self._current_year = None  # type: str
        self._n_elements_in_file = None  # type: int
        self._max_elements_in_file = 15000
        self._is_first_line = None  # type: bool

    @property
    def _output_extension(self) -> str:
        return 'json'

    def open_input_file(self, year: str) -> None:
        self._file_index = 1
        self._n_elements_in_file = 0
        self._current_year = year
        self._open_output_file()

    def _open_output_file(self) -> None:
        output_file_path = self.output_path / f'{self._current_year}_{self._file_index}.{self._output_extension}'
        self._current_file = open(str(output_file_path), 'w')
        self._current_file.write('[')
        self._is_first_line = True

    def handle_line(self, fields: List[str]) -> None:
        self._n_elements_in_file += 1
        if self._n_elements_in_file >= self._max_elements_in_file:
            self._close_output_file()
            self._n_elements_in_file = 0
            self._file_index += 1
            self._open_output_file()

        document = self._convert_to_document(fields)
        self._current_file.write(document)
        self._is_first_line = False

    def _convert_to_document(self, fields: List[str]) -> str:
        arxiv_id = clean_id(fields[id_index])
        authors = clean_authors(fields[authors_index])
        title = clean_title(fields[title_index])
        document = f"""{'' if self._is_first_line else ','}
      {{
        "type": "PUT",
        "document": {{
          "id": "{arxiv_id}",
          "fields": {{
            "year": "{self._current_year}",
            "authors": "{authors}",
            "title": "{title}"
          }}
        }}
      }}"""
        return document

    def close_input_file(self) -> None:
        self._close_file()

    def _close_output_file(self) -> None:
        self._close_file()

    def _close_file(self) -> None:
        if self._current_file is not None and not self._current_file.closed:
            self._current_file.write('\n]')
            self._current_file.close()

    def post_conversion(self) -> None:
        pass


class RedisConverter(Converter):
    def __init__(self, output_path_base: Path, clean_folder: bool):
        super().__init__(output_path_base, clean_folder, 'redis')
        self._file_index = None  # type: int
        self._writer = None  # type: csv.writer
        self._current_year = None  # type: str
        self._is_first_line = None  # type: bool

    @property
    def _output_extension(self) -> str:
        return 'csv'

    def open_input_file(self, year: str) -> None:
        self._current_year = year
        output_file_path = self.output_path / f'{self._current_year}.{self._output_extension}'
        output_file = open(str(output_file_path), 'w', newline='')
        self._writer = csv.writer(output_file)
        self._is_first_line = True

    def handle_line(self, fields: List[str]) -> None:
        document = self._convert_to_document(fields)
        self._writer.writerow(document)
        self._is_first_line = False

    def _convert_to_document(self, fields: List[str]) -> List[str]:
        arxiv_id = clean_id(fields[id_index])
        authors = clean_field(fields[authors_index]).replace(',', ', ')
        title = clean_field(fields[title_index])
        document = [arxiv_id, self._current_year, authors, title]
        return document

    def close_input_file(self) -> None:
        pass

    def post_conversion(self) -> None:
        pass


class PostgresConverter(Converter):
    def __init__(self, output_path_base: Path, clean_folder: bool):
        super().__init__(output_path_base, clean_folder, 'postgres')
        self._file_index = None  # type: int
        self._current_file = None  # type: TextIO
        self._current_year = None  # type: str
        self._is_first_line = None  # type: bool
        self._ids = set()

    @property
    def _output_extension(self) -> str:
        return 'sql'

    def open_input_file(self, year: str) -> None:
        self._current_year = year
        output_file_path = self.output_path / f'{self._current_year}.{self._output_extension}'
        self._current_file = open(str(output_file_path), 'w')
        self._current_file.write(f"""INSERT INTO refs (referencer, referencee)
VALUES""")
        self._is_first_line = True

    def handle_line(self, fields: List[str]) -> None:
        document = self._convert_to_document(fields)
        if document is not None:
            self._current_file.write(document)
            self._is_first_line = False

    def _convert_to_document(self, fields: List[str]) -> Optional[str]:
        arxiv_id = clean_id(fields[id_index])
        refs = fields[references_index].split(',')
        refs = [clean_id(r) for r in refs]
        if len(refs) == 1 and refs[0] == '':
            return None

        self._ids.add(arxiv_id)
        [self._ids.add(r) for r in refs]
        document = [('' if self._is_first_line and index == 0 else ',\n      ') + f" ('{arxiv_id}', '{r}')"
                    for index, r in enumerate(refs)]
        document = ''.join(document)
        return document

    def close_input_file(self) -> None:
        self._current_file.write('\n;')
        self._current_file.close()

    def post_conversion(self) -> None:
        create_tables_file_path = self.output_path / 'create_tables.sql'
        with open(str(create_tables_file_path), 'w') as create_tables_file:
            create_tables_file.write("""DROP TABLE IF EXISTS refs;
DROP TABLE IF EXISTS papers;

CREATE TABLE IF NOT EXISTS papers
(
  ID VARCHAR(64) PRIMARY KEY
);

CREATE TABLE IF NOT EXISTS refs
(
  referencer VARCHAR(64) NOT NULL,
  referencee VARCHAR(64) NOT NULL,
  FOREIGN KEY (referencer) REFERENCES papers (ID),
  FOREIGN KEY (referencee) REFERENCES papers (ID),
  PRIMARY KEY (referencer, referencee)
);""")

        insert_into_papers_file_path = self.output_path / 'insert_into_papers.sql'
        with open(str(insert_into_papers_file_path), 'w') as insert_into_papers_file:
            document = [('' if index == 0 else ',\n      ') + f" ('{r}')"
                        for index, r in enumerate(sorted(list(self._ids)))]
            document = ''.join(document)
            insert_into_papers_file.write(f"""INSERT INTO papers (ID)
VALUES{document}
;""")


def clean_folder_maybe(path: Path, clean_folder: bool, recreate: bool = True) -> None:
    if clean_folder and path.exists():
        logger.info(f'Cleaning folder {path.name}')
        shutil.rmtree(path)

    if recreate:
        path.mkdir(exist_ok=True, parents=True)


# only blast makes sense to cache
@click.command()
def main(source_url: str = 'https://github.com/paperscape/paperscape-data.git',
         n_max_splits: int = 7, max_elements_per_file: int = 15000, max_n_files: Optional[int] = 1,
         clean_input: bool = False, clean_output_for_blast: bool = True, clean_output_for_redis: bool = True,
         clean_output_for_postgres: bool = True) -> None:
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
    input_file_paths = sorted(input_file_paths, reverse=True)
    for index, input_file_path in enumerate(input_file_paths):
        if max_n_files is not None and index >= max_n_files:
            break

        logging.info(f'Converting {input_file_path.name}...')
        year = input_file_path.name[5:9]
        with open(str(input_file_path), 'r') as input_file:
            n_elements_in_file = 0

            [c.open_input_file(year) for c in converters]

            for line in input_file:
                line_clean = line.strip()
                if line_clean.startswith('#'):
                    continue

                n_elements_in_file += 1
                fields = line.split(';', n_max_splits)
                [c.handle_line(fields) for c in converters]

            [c.close_input_file() for c in converters]

            logging.info(f'N elements converted: {n_elements_in_file}')
            n_total_elements += n_elements_in_file

    [c.post_conversion() for c in converters]
    logging.info(f'N elements converted in total: {n_total_elements}')


def clone_repo(input_path, source_url):
    if not input_path.exists():
        logger.info('Cloning repo...')
        Repo.clone_from(source_url, input_path)
        logger.info('Finished cloning repo')


def clean_field(s: str) -> str:
    return s.replace('"', '').replace('\t', ' ').replace('\\', '\\\\').strip()


def clean_id(s: str) -> str:
    s = clean_field(s)
    s = pattern_alphanumeric.sub('_', s)
    return s


def clean_authors(s: str) -> str:
    s = clean_field(s)
    s = s.lower()
    s = [w.strip().split('.')[-1]
         for w in s.split(',')]
    s = [pattern_alpha.sub(' ', w) for w in s]
    [vocab.add(w) for w in s]
    s = ' '.join(s)
    return s


def clean_title(s: str) -> str:
    s = clean_field(s)
    s = s.lower()
    s = pattern_alpha.sub(' ', s)
    s = [stemmer.stem(w)
         for w in s.split()
         if w not in stop_words and len(w) > min_title_word_length]
    [vocab.add(w) for w in s]
    s = ' '.join(s)
    return s


if __name__ == '__main__':
    main()
