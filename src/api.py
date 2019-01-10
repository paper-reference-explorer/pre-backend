import redis
from flask import Flask, jsonify

app = Flask(__name__)
r = redis.StrictRedis('redis', 6379, 0, charset='utf-8', decode_responses=True)


@app.route('/')
def hello_world():
    return 'Hello World!'


@app.route('/api/v1/paper/<string:paper_id>')
def paper(paper_id: str):
    p = r.hgetall(paper_id)
    p['id'] = paper_id
    return jsonify(p)


@app.route('/api/v1/autocomplete/<string:query>')
def autocomplete(query: str):
    return f'Hello {query}!'


@app.route('/api/v1/references/<string:paper_id>')
def references(paper_id: str):
    return f'Hello {paper_id}!'


if __name__ == '__main__':
    app.run('0.0.0.0')
