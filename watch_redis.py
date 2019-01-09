from pathlib import Path
import logging
from watch_helper import wait_until_open

logging.basicConfig(format='%(asctime)s - %(levelname)-8s - %(name)s - %(message)s', level=logging.DEBUG)
logger = logging.getLogger(__name__)


def main(host: str = 'redis', port: int = 6379, file_glob: str = '*.csv') -> None:
    wait_until_open(host, port)
    base_path = Path('data')
    input_path = base_path / 'input'


if __name__ == '__main__':
    main()
