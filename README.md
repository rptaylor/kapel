# kapel
APEL accounting for Kubernetes.

## Requirements
- kube-state-metrics and Prometheus (installation via [bitnami/kube-prometheus](https://bitnami.com/stack/prometheus-operator/helm) is recommended)
  - All pod metrics that are collected via kube-state-metrics will be used, so you must set `.Values.kube-state-metrics.namespaces`
    to ensure that accounting records are only published for pods in the appropriate namespace.
  - Pods must specify CPU resource requests in order to be accounted.
  - You may wish to set some of the collectors in `.Values.kube-state-metrics.kubeResources` to False to disable collection of
    unnecessary metrics and reduce data volume. The required ones are `jobs` and `pods`.
  - For large production deployments, you should increase `.Values.prometheus.querySpec.timeout` to allow long queries to succeed.
  - You should ensure that the Prometheus deployment is configured to use persistent storage so the collected metrics data will be
    persisted for a sufficient period of time.
- X509 host certificate and key for publishing APEL records with ssmsend
- ssmsend container built using the provided Containerfile

## Helm chart installation
The kapel Helm chart is available from [this Helm repository](https://rptaylor.github.io/kapel/).
