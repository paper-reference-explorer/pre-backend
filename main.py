from pathlib import Path
import logging

from git import Repo

logging.basicConfig(format='%(asctime)s - %(levelname)-8s - %(name)s    - %(message)s', level=logging.DEBUG)
logger = logging.getLogger(__name__)


def main(source_url: str = 'https://github.com/paperscape/paperscape-data.git') -> None:
    path_base = Path('data')
    path_input = path_base / 'input'
    path_output = path_base / 'output'

    if not path_input.is_dir():
        logger.info('Cloning repo...')
        Repo.clone_from(source_url, path_input)
        logger.info('Finished cloning repo')
    path_output.mkdir(exist_ok=True, parents=True)


if __name__ == '__main__':
    main()
