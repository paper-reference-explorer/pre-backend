from pathlib import Path
import logging

from git import Repo

logging.basicConfig(format='%(asctime)s - %(levelname)-8s - %(name)s    - %(message)s', level=logging.DEBUG)
logger = logging.getLogger(__name__)


def main() -> None:
    base_path = Path('data')
    input_path = base_path / 'input'

    input_file_paths = input_path.glob('*.json')
    input_file_paths = sorted(input_file_paths, reverse=True)
    for input_file_path in input_file_paths:
        logging.info(f'Reading {input_file_path.name}...')


if __name__ == '__main__':
    main()
