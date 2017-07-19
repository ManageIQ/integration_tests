#!/bin/bash

curl -XGET http://admin:admin@10.12.23.122:9201/cfme-run.smem-2017.01.05/processes/_search?pretty=true -d @aggs/aggregations_unique_PIDS.json > results/unique_PIDS_result.json
curl -XGET http://admin:admin@10.12.23.122:9201/cfme-run.smem-2017.01.05/processes/_search?pretty=true -d @aggs/aggregations_RSS_desc_PID_name.json > results/PID_orderby_RSS_desc.json
