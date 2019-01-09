import logging
import socket
import time

logging.basicConfig(format='%(asctime)s - %(levelname)-8s - %(name)s - %(message)s', level=logging.DEBUG)
logger = logging.getLogger(__name__)


def wait_until_open(host: str, port: int) -> None:
    start_time = time.time()
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    connection_info = (host, port)
    result = sock.connect_ex(connection_info)
    while result != 0:
        logger.info('Port is not open')
        time.sleep(1)
        result = sock.connect_ex(connection_info)

    end_time = time.time()
    duration = end_time - start_time
    logging.info(f'Time passed: {duration:.02f}')
