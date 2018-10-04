from pathlib import Path
import logging

from git import Repo

logging.basicConfig(format='%(asctime)s - %(levelname)-8s - %(name)s    - %(message)s', level=logging.DEBUG)
logger = logging.getLogger(__name__)


def main(source_url: str = 'https://github.com/paperscape/paperscape-data.git') -> None:
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

    input_files = input_path.glob('*.csv')
    input_files = sorted(input_files, reverse=True)
    for input_file in input_files:
        logging.info(f'Converting {input_file.name}...')


if __name__ == '__main__':
    main()
