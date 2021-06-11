#!/usr/bin/python

# for low level API testing

import requests


PROMETHEUS_SERVER = 'http://kube-prometheus-prometheus.kube-prometheus:9090'
API='/api/v1/query'
TIMEOUT='500s'

QUERY_TIME = "2021-06-10T07:20:50.52Z"
QUERY_LENGTH = "12h"

CPUTIME_QUERY = f'(max_over_time(kube_pod_completion_time[{QUERY_LENGTH}]) - max_over_time(kube_pod_start_time[{QUERY_LENGTH}])) * on (exported_pod) group_left() max without (instance, pod) (max_over_time(kube_pod_container_resource_requests_cpu_cores{{node != ""}}[{QUERY_LENGTH}]))'
ENDTIME_QUERY = f'max_over_time(kube_pod_completion_time[{QUERY_LENGTH}])'
STARTTIME_QUERY = f'max_over_time(kube_pod_start_time[{QUERY_LENGTH}])'
CORES_QUERY = f'max_over_time(kube_pod_container_resource_requests_cpu_cores{{node != ""}}[{QUERY_LENGTH}])'

cputime_response = requests.get(PROMETHEUS_SERVER + API,
  params={
    'query': CPUTIME_QUERY,
    'time': QUERY_TIME,
    'timeout': TIMEOUT,
})
endtime_response = requests.get(PROMETHEUS_SERVER + API,
  params={
    'query': ENDTIME_QUERY,
    'time': QUERY_TIME,
    'timeout': TIMEOUT,
})
starttime_response = requests.get(PROMETHEUS_SERVER + API,
  params={
    'query': STARTTIME_QUERY,
    'time': QUERY_TIME,
    'timeout': TIMEOUT,
})
cores_response = requests.get(PROMETHEUS_SERVER + API,
  params={
    'query': CORES_QUERY,
    'time': QUERY_TIME,
    'timeout': TIMEOUT,
})

# These are lists of dicts.
# Each dict in the list contains:
# 'metric': a dict of key-value pairs of labels, one of which is the pod name (exported_pod)
# 'value': a list in which the 0th element is the timestamp of the value, 1th is the actual value we're interested in
cputime_results = cputime_response.json()['data']['result']
endtime_results = endtime_response.json()['data']['result']
starttime_results = starttime_response.json()['data']['result']
cores_results = cores_response.json()['data']['result']

# construct random-accessible dicts (instead of lists of dicts) so we can reference by the exported_pod label.
# cast from string to number while we're at it.
cputime = {item['metric']['exported_pod']:float(item['value'][1]) for item in cputime_results}
endtime = {item['metric']['exported_pod']:float(item['value'][1]) for item in endtime_results}
starttime = {item['metric']['exported_pod']:float(item['value'][1]) for item in starttime_results}
cores = {item['metric']['exported_pod']:float(item['value'][1]) for item in cores_results}

