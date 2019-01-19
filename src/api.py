import copy
import json
from typing import Dict, Optional

import requests
from flask import Flask, jsonify, abort

import config
import processing

app = Flask(__name__)
redis_connection = config.RedisServiceConfig.create_connection()
postgres_connection = config.PostgresServiceConfig.create_connection()


@app.route('/')
def hello_world():
    return 'Hello World!'


@app.route('/api/v1/paper/<string:paper_id>')
def paper(paper_id: str):
    p = _get_paper(paper_id)
    if p is None:
        p = dict()

    return jsonify(p)


@app.route('/api/v1/autocomplete/<string:query>')
def autocomplete(query: str):
    query = processing.clean_query(query)
    payload = copy.deepcopy(config.BlastServiceConfig.SEARCH_REQUEST_DICT)
    payload['search_request']['query']['query'] = query
    payload = json.dumps(payload)

    blast_response = requests.post(config.BlastServiceConfig.SEARCH_URL, data=payload)
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


@app.route('/api/v1/referenced_by/<string:paper_id>')
def references(paper_id: str):
    cursor = postgres_connection.cursor()

    cursor.execute(config.PostgresServiceConfig.REFERENCED_BY_SQL, dict(paper_id=paper_id))
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
        p['referenced_by_n'] = p.get('referenced_by_n', 0)
        return p
    else:
        return None


if __name__ == '__main__':
    app.run('0.0.0.0')
