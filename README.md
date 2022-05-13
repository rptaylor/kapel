# kapel
APEL accounting for Kubernetes.

## Requirements
- X509 certificate and key for publishing APEL records with ssmsend
  - Note: ssmsend only uses the certificate for content signing, not TLS, so the DN of the certificate does not need to match any host name. It only needs to match the "Host DN" field in GOCDB for the gLite-APEL service.
- ssmsend container built using the provided Containerfile and pushed to an accessible registry server
- kube-state-metrics and Prometheus (installation via [bitnami/kube-prometheus](https://bitnami.com/stack/prometheus-operator/helm) is recommended)
  - All pod metrics that are collected via kube-state-metrics will be used, so you must set `.Values.kube-state-metrics.namespaces`
    to ensure that accounting records are only published for pods in the appropriate namespace(s).
  - Pods must specify CPU resource requests in order to be accounted.
  - You may wish to set some of the collectors in `.Values.kube-state-metrics.kubeResources` to False to disable collection of
    unnecessary metrics and reduce data volume. Only the `pods` collector is required.
  - You should ensure that the Prometheus deployment is configured to use persistent storage so the collected metrics data will be
    persisted for a sufficient period of time.
  - For large production deployments (examples are based on a cluster with about 125 nodes and 7000 cores):
    - Increase `.Values.prometheus.querySpec.timeout` (e.g. ~ 1800s) to allow long queries to succeed.
    - Apply sufficient resource requests and limits, e.g.
```
prometheus:
  resources:
    requests:
      cpu: "2000m"
      memory: "16Gi"
    limits:
      cpu: "8000m"
      memory: "32Gi"

kube-state-metrics:
  resources:
    limits: 
      cpu: 2000m
      memory: 2048Mi
    requests: 
      cpu: 200m
      memory: 256Mi
```

## Helm chart installation
The kapel Helm chart is available from [this Helm repository](https://rptaylor.github.io/kapel/).
