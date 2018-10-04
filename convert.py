from pathlib import Path
import logging

from git import Repo

logging.basicConfig(format='%(asctime)s - %(levelname)-8s - %(name)s    - %(message)s', level=logging.DEBUG)
logger = logging.getLogger(__name__)


def clean_field(s: str) -> str:
    return s.replace('"', '').replace('\t', ' ').replace('\\', '\\\\')


def main(source_url: str = 'https://github.com/paperscape/paperscape-data.git',
         n_max_splits: int = 7) -> None:
    base_path = Path('data')
    input_path = base_path / 'input'
    output_path = base_path / 'output'

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

        output_file_path = output_path / f'{year}.json'
        with open(str(output_file_path), 'w') as output_file:
            output_file.write('[')

            is_first_line = True
            with open(str(input_file_path), 'r') as input_file:
                for line in input_file:
                    line_clean = line.strip()
                    if not line_clean.startswith('#'):
                        fields = line_clean.split(';', n_max_splits)
                        arxiv_id = clean_field(fields[0])
                        authors = clean_field(fields[5])
                        authors = authors.replace(',', ', ')
                        title = clean_field(fields[-1])

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
                        output_file.write(document)
                        is_first_line = False
                        
            output_file.write('\n]')


if __name__ == '__main__':
    main()
