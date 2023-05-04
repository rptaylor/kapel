#!/usr/bin/python

# for low level API testing

import requests


PROMETHEUS_SERVER = 'http://kube-prometheus-prometheus.kube-prometheus:9090'
API='/api/v1/query'
TIMEOUT='500s'

def doQueries(instant, duration):
  CPUTIME_QUERY = f'(max_over_time(kube_pod_completion_time[{duration}]) - max_over_time(kube_pod_start_time[{duration}])) * on (pod) group_left() max without (instance) (max_over_time(kube_pod_container_resource_requests{{resource="cpu", node != ""}}[{duration}]))'
  ENDTIME_QUERY = f'max_over_time(kube_pod_completion_time[{duration}])'
  STARTTIME_QUERY = f'max_over_time(kube_pod_start_time[{duration}])'
  CORES_QUERY = f'max_over_time(kube_pod_container_resource_requests{{resource="cpu", node != ""}}[{duration}])'

  cputime_response = requests.get(PROMETHEUS_SERVER + API,
    params={
      'query': CPUTIME_QUERY,
      'time': instant,
      'timeout': TIMEOUT,
  })
  endtime_response = requests.get(PROMETHEUS_SERVER + API,
    params={
      'query': ENDTIME_QUERY,
      'time': instant,
      'timeout': TIMEOUT,
  })
  starttime_response = requests.get(PROMETHEUS_SERVER + API,
    params={
      'query': STARTTIME_QUERY,
      'time': instant,
      'timeout': TIMEOUT,
  })
  cores_response = requests.get(PROMETHEUS_SERVER + API,
    params={
      'query': CORES_QUERY,
      'time': instant,
      'timeout': TIMEOUT,
  })

# These are lists of dicts.
# Each dict in the list contains:
# 'metric': a dict of key-value pairs of labels, one of which is the pod name 
# 'value': a list in which the 0th element is the timestamp of the value, 1th is the actual value we're interested in
  cputime_results = cputime_response.json()['data']['result']
  endtime_results = endtime_response.json()['data']['result']
  starttime_results = starttime_response.json()['data']['result']
  cores_results = cores_response.json()['data']['result']

# construct random-accessible dicts (instead of lists of dicts) so we can reference by the pod label.
# cast from string to number while we're at it.
  cputime = {item['metric']['pod']:float(item['value'][1]) for item in cputime_results}
  endtime = {item['metric']['pod']:float(item['value'][1]) for item in endtime_results}
  starttime = {item['metric']['pod']:float(item['value'][1]) for item in starttime_results}
  cores = {item['metric']['pod']:float(item['value'][1]) for item in cores_results}

  print(len(cputime))
  print(len(endtime))
  print(len(starttime))
  print(len(cores))
  return cputime, endtime, starttime, cores

doQueries("2021-06-11T00:00:00.00Z", "24h")
