import csv
import logging
import math
import re
import shutil
from pathlib import Path
from typing import TextIO, Tuple, Optional, List

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
ids = set()


def main(source_url: str = 'https://github.com/paperscape/paperscape-data.git',
         n_max_splits: int = 7, max_elements_per_file: int = 15000, max_n_files: Optional[int] = 1,
         clean_input: bool = False, clean_output_for_blast: bool = False, clean_output_for_redis: bool = True,
         clean_output_for_postgres: bool = False) -> None:
    # warning: redis recreates the tables and inserts elements
    # if a file is cached it won't get added
    # hence, for now, redis always has to run

    base_path = Path('data')
    input_path = base_path / 'input'
    output_path_base = base_path / 'output_for'
    output_path_blast = output_path_base / 'blast'
    output_path_redis = output_path_base / 'redis'
    output_path_postgres = output_path_base / 'postgres'
    n_total_elements = 0
    setup_directories(input_path, clean_input, output_path_blast, clean_output_for_blast,
                      output_path_redis, clean_output_for_redis, output_path_postgres, clean_output_for_postgres,
                      source_url)

    input_file_paths = input_path.glob('*.csv')
    input_file_paths = sorted(input_file_paths, reverse=True)
    for index, input_file_path in enumerate(input_file_paths):
        if max_n_files is not None and index >= max_n_files:
            break

        logging.info(f'Converting {input_file_path.name}...')
        year = input_file_path.name[5:9]
        n_elements_in_file = count_elements_in_file(input_file_path)
        n_files_needed = math.ceil(n_elements_in_file / max_elements_per_file)
        with open(str(input_file_path), 'r') as input_file:
            n_elements_in_file = 0
            for file_index in range(n_files_needed):
                output_file_path_blast = get_output_file_path(file_index, output_path_blast, year, 'json')
                output_file_path_redis = get_output_file_path(file_index, output_path_redis, year, 'csv')
                output_file_path_postgres = get_output_file_path(file_index, output_path_postgres, year, 'sql')
                if (output_file_path_blast.exists() and output_file_path_redis.exists()
                        and output_file_path_postgres.exists()):
                    logging.info(f'File {output_file_path_blast.name} or File {output_file_path_redis.name}'
                                 + f' or File {output_file_path_postgres.name} already exists. Skipping.')
                else:
                    n_elements_in_file += write_content(input_file, output_file_path_blast, output_file_path_redis,
                                                        output_file_path_postgres, max_elements_per_file, n_max_splits,
                                                        year)
            logging.info(f'N elements converted: {n_elements_in_file}')
            n_total_elements += n_elements_in_file
            logging.info(f'vocab size so far: {len(vocab)}')

    create_tables_file_path = output_path_postgres / 'create_tables.sql'
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

    insert_into_papers_file_path = output_path_postgres / 'insert_into_papers.sql'
    with open(str(insert_into_papers_file_path), 'w') as insert_into_papers_file:
        document = [('' if index == 0 else ',\n      ') + f" ('{r}')"
                    for index, r in enumerate(sorted(list(ids)))]
        document = ''.join(document)
        insert_into_papers_file.write(f"""INSERT INTO papers (ID)
VALUES{document}
;""")

    logging.info(f'N elements converted in total: {n_total_elements}')
    logging.info(f'vocab size total: {len(vocab)}')


def get_output_file_path(file_index: int, output_path: Path, year: str, extension: str) -> Path:
    output_file_path = output_path / f'{year}_{file_index + 1}.{extension}'
    return output_file_path


def setup_directories(input_path: Path, clean_input: bool, output_path_blast: Path, clean_output_for_blast: bool,
                      output_path_redis: Path, clean_output_for_redis: bool,
                      output_path_postgres: Path, clean_output_for_postgres: bool, source_url: str) -> None:
    clean_folder_maybe(input_path, clean_input, recreate=False)
    clean_folder_maybe(output_path_blast, clean_output_for_blast)
    clean_folder_maybe(output_path_redis, clean_output_for_redis)
    clean_folder_maybe(output_path_postgres, clean_output_for_postgres)
    if not input_path.exists():
        logger.info('Cloning repo...')
        Repo.clone_from(source_url, input_path)
        logger.info('Finished cloning repo')


def clean_folder_maybe(path: Path, clean_folder: bool, recreate: bool = True) -> None:
    if clean_folder and path.exists():
        logger.info(f'Cleaning folder {path.name}')
        shutil.rmtree(path)

    if recreate:
        path.mkdir(exist_ok=True, parents=True)


def count_elements_in_file(input_file_path: Path) -> int:
    n_elements_in_file = 0
    with open(str(input_file_path), 'r') as input_file:
        for line in input_file:
            line_clean = line.strip()
            if not line_clean.startswith('#'):
                n_elements_in_file += 1
    return n_elements_in_file


def write_content(input_file: TextIO, output_file_path_blast: Path, output_file_path_redis: Path,
                  output_file_path_postgres: Path, max_elements_per_file: int, n_max_splits: int, year: str) -> int:
    with open(str(output_file_path_blast), 'w') as output_file_blast:
        output_file_blast.write('[')
        with open(str(output_file_path_redis), 'w', newline='') as output_file_redis:
            writer_redis = csv.writer(output_file_redis)

            with open(str(output_file_path_postgres), 'w', newline='') as output_file_postgres:
                output_file_postgres.write(f"""INSERT INTO refs (referencer, referencee)
VALUES""")

                n_elements = 0
                is_first_line_blast = True
                is_first_line_redis = True
                is_first_line_postgres = True
                for line in input_file:
                    line_clean = line.strip()
                    if not line_clean.startswith('#'):
                        n_elements += 1
                        fields = line.split(';', n_max_splits)

                        data = extract_fields_blast(fields)
                        document = convert_to_document_blast(year, is_first_line_blast, data)
                        output_file_blast.write(document)
                        is_first_line_blast = False

                        data = extract_fields_redis(fields)
                        document = convert_to_document_redis(year, is_first_line_redis, data)
                        writer_redis.writerow(document)
                        is_first_line_redis = False

                        data = extract_fields_postgres(fields)
                        document = convert_to_document_postgres(year, is_first_line_postgres, data)
                        if document is not None:
                            output_file_postgres.write(document)
                            is_first_line_postgres = False

                        if n_elements == max_elements_per_file:
                            break

                output_file_postgres.write('\n;')
        output_file_blast.write('\n]')

    return n_elements


def extract_fields_blast(fields: List[str]) -> Tuple[str, str, str]:
    arxiv_id = clean_id(fields[id_index])
    authors = clean_authors(fields[authors_index])
    title = clean_title(fields[title_index])
    return arxiv_id, authors, title


def convert_to_document_blast(year: str, is_first_line: bool, fields: Tuple[str, str, str]) -> str:
    arxiv_id, authors, title = fields
    document = f"""{'' if is_first_line else ','}
  {{
    "type": "PUT",
    "document": {{
      "id": "{arxiv_id}",
      "fields": {{
        "year": "{year}",
        "authors": "{authors}",
        "title": "{title}"
      }}
    }}
  }}"""
    return document


def extract_fields_redis(fields: List[str]) -> Tuple[str, str, str]:
    arxiv_id = clean_id(fields[id_index])
    authors = clean_field(fields[authors_index]).replace(',', ', ')
    title = clean_field(fields[title_index])
    return arxiv_id, authors, title


def convert_to_document_redis(year: str, is_first_line: bool, fields: Tuple[str, str, str]) -> List[str]:
    arxiv_id, authors, title = fields
    document = [arxiv_id, year, authors, title]
    return document


def extract_fields_postgres(fields: List[str]) -> Tuple[str, List[str]]:
    arxiv_id = clean_id(fields[id_index])
    refs = fields[references_index].split(',')
    refs = [clean_id(r) for r in refs]
    return arxiv_id, refs


def convert_to_document_postgres(year: str, is_first_line: bool, fields: Tuple[str, List[str]]) -> Optional[str]:
    arxiv_id, refs = fields
    if len(refs) == 1 and refs[0] == '':
        return None
    ids.add(arxiv_id)
    [ids.add(r) for r in refs]
    document = [('' if is_first_line and index == 0 else ',\n      ') + f" ('{arxiv_id}', '{r}')"
                for index, r in enumerate(refs)]
    document = ''.join(document)
    return document


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
