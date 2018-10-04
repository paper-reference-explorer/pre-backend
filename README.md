This repository provides the backend for the paper-references-explorer website. It offers two basic functionalities: search for a paper and generation of the graph data for a set of papers.

## run example data
`sudo docker-compose up`
### test data storage
```bash
curl -X PUT 'http://127.0.0.1:10002/rest/A_my' -d @./example-data/doc_A.json
curl -X GET 'http://127.0.0.1:10002/rest/A_my'
```

### test search
```bash
curl -X POST 'http://127.0.0.1:10002/rest/_bulk' -d @./example-data/bulk_put_request.json
curl -X POST 'http://127.0.0.1:10002/rest/_search?pretty-print=true' -d @./example-data/search_request.json
```
