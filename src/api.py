import copy
import json
from typing import Dict

import redis
import requests
from flask import Flask, jsonify, abort

app = Flask(__name__)
redis_connection = redis.StrictRedis('redis', 6379, 0, charset='utf-8', decode_responses=True)

blast_host = 'blast'
blast_port = 10002

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

    blast_response = requests.post(f'http://{blast_host}:{blast_port}/rest/_search', data=payload)
    if blast_response.status_code != 200:
        abort(blast_response.status_code)

    blast_response = json.loads(blast_response.content.decode())
    if blast_response['success']:
        hits = blast_response['search_result']['hits']
        result = [_get_paper(h['id']) for h in hits]
    else:
        result = []

    return jsonify(result)


@app.route('/api/v1/references/<string:paper_id>')
def references(paper_id: str):
    return f'Hello {paper_id}!'


def _get_paper(paper_id: str) -> Dict[str, str]:
    p = redis_connection.hgetall(paper_id)
    p['id'] = paper_id
    return p


if __name__ == '__main__':
    app.run('0.0.0.0')
