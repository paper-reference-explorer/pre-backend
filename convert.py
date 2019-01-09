from pathlib import Path
import logging
import math
from typing import TextIO
import re

from git import Repo
import nltk

nltk.download('stopwords')

logging.basicConfig(format='%(asctime)s - %(levelname)-8s - %(name)s    - %(message)s', level=logging.DEBUG)
logger = logging.getLogger(__name__)

pattern_alpha = re.compile('[^a-zA-Z ]+')
pattern_alphanumeric = re.compile('[\W]+')
stop_words = set(nltk.corpus.stopwords.words('english'))
stemmer = nltk.stem.SnowballStemmer('english')
vocab = set()


def clean_field(s: str) -> str:
    return s.replace('"', '').replace('\t', ' ').replace('\\', '\\\\')


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
         if w not in stop_words and len(w) > 3]
    [vocab.add(w) for w in s]
    s = ' '.join(s)
    return s


# add output cache with overwrite argument
def main(source_url: str = 'https://github.com/paperscape/paperscape-data.git',
         n_max_splits: int = 7, max_elements_per_file: int = 15000) -> None:
    base_path = Path('data')
    input_path = base_path / 'input'
    output_path = base_path / 'output'
    n_total_elements = 0

    # path might already exist
    # for example, in case the directory is mounted in docker
    if not input_path.exists():
        logger.info('Cloning repo...')
        Repo.clone_from(source_url, input_path)
        logger.info('Finished cloning repo')
    output_path.mkdir(exist_ok=True, parents=True)

    input_file_paths = input_path.glob('*.csv')
    input_file_paths = sorted(input_file_paths, reverse=True)
    for input_file_path in input_file_paths:
        logging.info(f'Converting {input_file_path.name}...')
        year = input_file_path.name[5:9]

        n_elements_in_file = 0
        with open(str(input_file_path), 'r') as input_file:
            for line in input_file:
                line_clean = line.strip()
                if not line_clean.startswith('#'):
                    n_elements_in_file += 1

        with open(str(input_file_path), 'r') as input_file:
            n_files_needed = math.ceil(n_elements_in_file / max_elements_per_file)
            n_elements_in_file = 0
            for file_index in range(n_files_needed):
                output_file_path = output_path / f'{year}_{file_index + 1}.json'
                with open(str(output_file_path), 'w') as output_file:
                    output_file.write('[')
                    n_elements_in_file += write_content(input_file, output_file, max_elements_per_file, n_max_splits,
                                                        year)
                    output_file.write('\n]')
            logging.info(f'N elements converted: {n_elements_in_file}')
            n_total_elements += n_elements_in_file
            logging.info(f'vocab size so far: {len(vocab)}')

    logging.info(f'N elements converted in total: {n_total_elements}')
    logging.info(f'vocab size total: {len(vocab)}')


def write_content(input_file: TextIO, output_file: TextIO, max_elements_per_file: int,
                  n_max_splits: int, year: str) -> int:
    n_elements = 0
    for line in input_file:
        line_clean = line.strip()
        if not line_clean.startswith('#'):
            n_elements += 1
            is_first_line = n_elements == 1
            document = convert_to_json_string(line_clean, is_first_line, n_max_splits, year)
            output_file.write(document)
            if n_elements == max_elements_per_file:
                break
    return n_elements


def convert_to_json_string(line: str, is_first_line: bool, n_max_splits: int, year: str) -> str:
    fields = line.split(';', n_max_splits)
    arxiv_id = clean_id(fields[0])
    authors = fields[5]
    authors_cleaned = clean_authors(authors)
    authors = clean_field(authors).replace(',', ', ')
    title = fields[-1]
    title_cleaned = clean_title(title)
    title = clean_field(title)
    document = f"""{'' if is_first_line else ','}
  {{
    "type": "PUT",
    "document": {{
      "id": "{arxiv_id}",
      "fields": {{
        "year": "{year}",
        "authors": "{authors_cleaned}",
        "title": "{title_cleaned}",
        "_authors": "{authors}",
        "_title": "{title}"
      }}
    }}
  }}"""
    return document


if __name__ == '__main__':
    main()
