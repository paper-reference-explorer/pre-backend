import logging

logging.basicConfig(format='%(asctime)s - %(levelname)-8s - %(name)s - %(message)s', level=logging.DEBUG)
logger = logging.getLogger(__name__)


def main() -> None:
    logger.info('Hello, world!')


if __name__ == '__main__':
    main()
