import copy
import json
from typing import Dict, Optional

import psycopg2
import redis
import requests
from flask import Flask, jsonify, abort

app = Flask(__name__)
redis_connection = redis.StrictRedis('redis', 6379, 0, charset='utf-8', decode_responses=True)

blast_url = f'http://blast:10002/rest/_search'

redis_host = 'redis'
redis_port = 6379
redis_db = 0

blast_request = {
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

postgres_connection_string = "host='postgres' port=5432 dbname=postgres user=postgres password=mysecretpassword"
postgres_connection = psycopg2.connect(postgres_connection_string)
postgres_select_sql = "SELECT referencee FROM refs WHERE referencer = %(paper_id)s"


@app.route('/')
def hello_world():
    return 'Hello World!'


@app.route('/api/v1/paper/<string:paper_id>')
def paper(paper_id: str):
    p = _get_paper(paper_id)
    return jsonify(p)


@app.route('/api/v1/autocomplete/<string:query>')
def autocomplete(query: str):
    payload = copy.deepcopy(blast_request)
    payload['search_request']['query']['query'] = query
    payload = json.dumps(payload)

    blast_response = requests.post(blast_url, data=payload)
    if blast_response.status_code != 200:
        abort(blast_response.status_code)

    blast_response = json.loads(blast_response.content.decode())
    if blast_response['success']:
        hits = blast_response['search_result']['hits']
        result = [_get_paper(h['id']) for h in hits]
        result = [r for r in result if r is not None]
    else:
        result = []

    return jsonify(result)


@app.route('/api/v1/references/<string:paper_id>')
def references(paper_id: str):
    cursor = postgres_connection.cursor()

    cursor.execute(postgres_select_sql, dict(paper_id=paper_id))
    postgres_result = cursor.fetchall()
    if len(postgres_result) > 0:
        result = [_get_paper(r[0]) for r in postgres_result]
        result = [r for r in result if r is not None]
    else:
        result = []

    postgres_connection.commit()
    cursor.close()
    return jsonify(result)


def _get_paper(paper_id: str) -> Optional[Dict[str, str]]:
    p = redis_connection.hgetall(paper_id)
    if len(p.keys()) > 0:
        p['id'] = paper_id
        return p
    else:
        return None


if __name__ == '__main__':
    app.run('0.0.0.0')
