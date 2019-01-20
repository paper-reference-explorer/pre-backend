import abc
from typing import Dict, List

import psycopg2
import redis


class InputConfig:
    SOURCE_URL = 'https://github.com/paperscape/paperscape-data.git'
    N_MAX_SPLITS = 7
    ID_INDEX = 0
    CATEGORIES_INDEX = 1
    REFERENCES_INDEX = 4
    AUTHORS_INDEX = 5
    TITLE_INDEX = 6
    INPUT_FOLDER_NAME = 'input'
    FILE_GLOB = '*.csv'


class ServiceConfig(abc.ABC):

    @property
    @abc.abstractmethod
    def HOST(self) -> str:
        pass

    @property
    @abc.abstractmethod
    def PORT(self) -> int:
        pass

    @property
    @abc.abstractmethod
    def FILE_EXTENSION(self) -> str:
        pass

    @property
    @abc.abstractmethod
    def FOLDER_NAME(self) -> str:
        pass

    @property
    def FILE_GLOB(self) -> str:
        return f'*.{self.FILE_EXTENSION}'


class _BlastServiceConfig(ServiceConfig):

    @property
    def HOST(self) -> str:
        return 'blast'

    @property
    def PORT(self) -> int:
        return 10002

    @property
    def FILE_EXTENSION(self) -> str:
        return 'json'

    @property
    def FOLDER_NAME(self) -> str:
        return 'blast'

    @property
    def FILE_START(self) -> str:
        return '['

    def FILE_ENTRY(self, is_first_line: bool, paper_id: str, year: str, authors: str, title: str) -> str:
        return f"""{'' if is_first_line else ','}
      {{
        "type": "PUT",
        "document": {{
          "id": "{paper_id}",
          "fields": {{
            "year": "{year}",
            "authors": "{authors}",
            "title": "{title}"
          }}
        }}
      }}"""

    @property
    def FILE_END(self) -> str:
        return '\n]'

    @property
    def _URL_BASE(self) -> str:
        return f'http://{self.HOST}:{self.PORT}/rest'

    @property
    def POST_URL(self) -> str:
        return f'{self._URL_BASE}/_bulk'

    @property
    def SEARCH_URL(self) -> str:
        return f'{self._URL_BASE}/_search'

    @property
    def SEARCH_REQUEST_DICT(self) -> Dict:
        return {
            "search_request": {
                "query": {
                    "query": None
                },
                "size": 10,
                "from": 0,
                "fields": [
                    "*"
                ],
                "sort": [
                    "-_score"
                ],
                "facets": {},
                "highlight": {}
            }
        }


class _PostgresServiceConfig(ServiceConfig):

    @property
    def HOST(self) -> str:
        return 'postgres'

    @property
    def PORT(self) -> int:
        return 5432

    @property
    def FILE_EXTENSION(self) -> str:
        return 'sql'

    @property
    def FOLDER_NAME(self) -> str:
        return 'postgres'

    @property
    def DB_NAME(self) -> str:
        return 'postgres'

    @property
    def USER_NAME(self) -> str:
        return 'postgres'

    @property
    def CONNECTION_STRING(self) -> str:
        return (f"host='{self.HOST}' port={self.PORT} dbname={self.DB_NAME} user={self.USER_NAME}"
                + f" password=mysecretpassword")

    def create_connection(self) -> psycopg2.extensions.connection:
        return psycopg2.connect(self.CONNECTION_STRING)

    @property
    def CREATE_TABLE_FILE_NAME(self) -> str:
        return f'create_tables.{self.FILE_EXTENSION}'

    @property
    def INSERT_INTO_PAPERS_FILE_NAME(self) -> str:
        return f'insert_into_papers.{self.FILE_EXTENSION}'

    @property
    def CREATE_TABLES_SQL(self) -> str:
        return """DROP TABLE IF EXISTS refs;
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
);"""

    @property
    def INSERT_INTO_REFS_START(self) -> str:
        return """INSERT INTO refs (referencer, referencee)
VALUES"""

    def INSERT_INTO_REFS_ENTRY(self, is_first_line: bool, paper_id: str, refs: List[str]) -> str:
        document = [('' if is_first_line and index == 0 else ',\n      ') + f" ('{paper_id}', '{r}')"
                    for index, r in enumerate(refs)]
        document = ''.join(document)
        return document

    @property
    def INSERT_INTO_REFS_END(self) -> str:
        return '\n;'

    def INSERT_INTO_PAPERS_SQL(self, ids: set) -> str:
        document = [('' if index == 0 else ',\n      ') + f" ('{r}')"
                    for index, r in enumerate(sorted(list(ids)))]
        document = ''.join(document)
        document = f"""INSERT INTO papers (ID)
VALUES{document}
;"""
        return document

    @property
    def REFERENCED_BY_SQL(self) -> str:
        return 'SELECT referencer FROM refs WHERE referencee = %(paper_id)s'


class _RedisServiceConfig(ServiceConfig):
    @property
    def HOST(self) -> str:
        return 'redis'

    @property
    def PORT(self) -> int:
        return 6379

    @property
    def FILE_EXTENSION(self) -> str:
        return 'csv'

    @property
    def FOLDER_NAME(self) -> str:
        return 'redis'

    @property
    def DB(self) -> int:
        return 0

    def create_connection(self) -> redis.Redis:
        return redis.StrictRedis(host=self.HOST, port=self.PORT, db=self.DB, charset='utf-8', decode_responses=True)


BlastServiceConfig = _BlastServiceConfig()
PostgresServiceConfig = _PostgresServiceConfig()
RedisServiceConfig = _RedisServiceConfig()

LOG_FORMAT = '%(asctime)s - %(levelname)-8s - %(name)s    - %(message)s'
