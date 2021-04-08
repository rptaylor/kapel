# kapel
APEL accounting for Kubernetes.

## Requirements
- kube-state-metrics and Prometheus (installation via [bitnami/kube-prometheus](https://bitnami.com/stack/prometheus-operator/helm) is recommended)
  - All pod metrics that are collected via kube-state-metrics will be used, so you must set `kube-state-metrics.namespace` 
    in the chart values to ensure that accounting records are only published for pods in the appropriate namespace.
  - You should ensure that the Prometheus deployment is configured to use persistent storage so the collected metrics data will be
    persisted for a sufficient period of time.
- X509 host certificate and key for publishing APEL records with ssmsend
- ssmsend container built using the provided Dockerfile
