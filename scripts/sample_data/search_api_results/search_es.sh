#!/bin/bash

curl -XGET 'http://admin:admin@10.12.23.122:9201/cfme-run.smem-2017.01.05/processes/_search?pretty=true&size=1' > results/doctype:processes_sample.json
curl -XGET 'http://admin:admin@10.12.23.122:9201/cfme-run.smem-2017.01.05/appliance_memory/_search?pretty=true&size=1' > results/doctype:appliance_memory_sample.json
curl -XGET 'http://admin:admin@10.12.23.122:9201/cfme-run.summary-2017.01.05//_search?pretty=true&size=1' > results/doctype:summary_sample.json
