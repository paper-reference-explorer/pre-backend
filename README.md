This repository provides the backend for the paper-references-explorer website. It offers two basic functionalities: search for a paper and generation of the graph data for a set of papers.

## run example data
curl -X PUT 'http://127.0.0.1:10002/rest/A_my' -d @./doc_A.json
curl -X GET 'http://127.0.0.1:10002/rest/A_my'

curl -X POST 'http://127.0.0.1:10002/rest/_bulk' -d @./bulk_put_request.json
curl -X POST 'http://localhost:10002/rest/_search?pretty-print=true' -d @./search_request.json
