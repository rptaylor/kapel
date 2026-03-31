#!/usr/bin/env python3
import os, time, sys
from datetime import datetime, timezone
from kubernetes import client, config
from prometheus_client import start_http_server, Gauge

# prometheus metrics
pod_endtime   = Gauge('kuantifier_pod_endtime',   'Pod end time (unix seconds)',   ['namespace','pod','uid'])
pod_last_seen = Gauge('kuantifier_pod_last_seen', 'Last time the pod was seen (unix seconds)', ['namespace','pod','uid'])
pod_cpu_req   = Gauge('kuantifier_pod_cpu_requests', 'CPU requests (cores)', ['namespace','pod','uid'])

# config variables 
NAMESPACE   = os.environ.get('NAMESPACE', 'default')
METRICS_PORT      = int(os.environ.get('METRICS_PORT', '9100'))
SCAN_INTERVAL     = int(os.environ.get('SCAN_INTERVAL_SECONDS', '30'))
#number of scans before a pod is considered gone
MISSING_TOLERANCE = int(os.environ.get('MISSING_TOLERANCE', '1'))

# Prefix for identifying workload pods
POD_NAME_PREFIX   = os.environ.get('POD_NAME_PREFIX', 'jupyter-')

if __name__ == '__main__':
    start_http_server(METRICS_PORT)
    try:
        config.load_incluster_config()
    except Exception:
        config.load_kube_config()
    v1 = client.CoreV1Api()

    last_seen_map = {} 
    miss_count    = {}  

    print(f"[exporter] Watching namespace {NAMESPACE} on port {METRICS_PORT}", file=sys.stderr)

    while True:
        now = datetime.now(timezone.utc).timestamp()
        try:
            pods = v1.list_namespaced_pod(NAMESPACE).items
            current = set()

            # gets all the jupyter pods
            for pod in pods:
                name = pod.metadata.name or ""
                if not name.startswith(POD_NAME_PREFIX):
                    continue
                uid = pod.metadata.uid
                ns = pod.metadata.namespace
                key = (ns, name, uid)
                current.add(key)

                # last seen updates
                last_seen_map[key] = now
                pod_last_seen.labels(*key).set(now)

                # get cpu requests
                cpu_req = 0.0
                for c in (pod.spec.containers or []):
                    if c.resources and c.resources.requests:
                        val = c.resources.requests.get('cpu')
                        if not val:
                            continue
                        s = str(val)
                        if s.endswith('m'):
                            cpu_req += float(s[:-1]) / 1000.0
                        else:
                            cpu_req += float(s)
                if cpu_req > 0:
                    pod_cpu_req.labels(*key).set(cpu_req)

                # catches terminating pods and marks them with the kuantifier_pod_endtime metric
                phase = pod.status.phase or ""
                if phase in ('Succeeded', 'Failed') or pod.metadata.deletion_timestamp:
                    pod_endtime.labels(*key).set(now)

            # gets pods that stopped before KSM could see them
            previously = set(last_seen_map.keys())
            disappeared = previously - current
            for key in disappeared:
                miss_count[key] = miss_count.get(key, 0) + 1
                if miss_count[key] >= MISSING_TOLERANCE:
                    end_ts = last_seen_map.get(key, now)
                    pod_endtime.labels(*key).set(end_ts)
                    last_seen_map.pop(key, None)
                    miss_count.pop(key, None)

            # reset the scan missing count if a pod is still there
            for key in current:
                miss_count.pop(key, None)

        except Exception as e:
            print(f"[error] {e}", file=sys.stderr)

        time.sleep(SCAN_INTERVAL)
