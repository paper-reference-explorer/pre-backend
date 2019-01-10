from flask import Flask

app = Flask(__name__)


@app.route('/')
def hello_world():
    return 'Hello World!'


@app.route('/api/v1/paper/<string:paper_id>')
def paper(paper_id: str):
    return f'Hello {paper_id}!'


@app.route('/api/v1/autocomplete/<string:query>')
def autocomplete(query: str):
    return f'Hello {query}!'


@app.route('/api/v1/references/<string:paper_id>')
def references(paper_id: str):
    return f'Hello {paper_id}!'


if __name__ == '__main__':
    app.run()
