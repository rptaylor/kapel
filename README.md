# KAPEL 
KAPEL is container-native APEL accounting for Kubernetes.
- Lightweight and stateless (data storage is handled by Prometheus).
- Supports two publishing modes:
  - 'auto' mode to publish the current month and previous month.
  - 'gap' mode to (re)publish an arbitrary fixed time period.
- Supports two data source modes:
  - Normally, pod data is retrieved from Prometheus.
  - For manual corrections, you can supply the accounting data to be published yourself.
- Supports two data outlets:
  - "ssmsend" publishes records to APEL via ssmsend
  - "gratia" publishes records to [GRACC](https://gracc.opensciencegrid.org/) via 
    [Gratia](https://github.com/opensciencegrid/gratia-probe/)

## Requirements
- X509 certificate and key for publishing APEL records with ssmsend
  - Note: ssmsend only uses the certificate for content signing, not TLS, so the DN of the certificate does not need to match any host name.
    It only needs to match the "Host DN" field in GOCDB for the gLite-APEL service.
- kube-state-metrics and Prometheus (installing both via [bitnami/kube-prometheus](https://bitnami.com/stack/prometheus-operator/helm) is recommended)
  - You may wish to disable collection of some resources in `.Values.kube-state-metrics.kubeResources` to reduce the volume of unnecessary data.
    Only the collection of `pods` resources is required.
  - You should ensure that the Prometheus deployment is configured to use persistent storage so the collected metrics data will be
    persisted for a sufficient period of time (e.g. at least a couple months).
  - kube-state-metrics should be configured with `honorLabels: true`
    - This is more intuitive, and set by default in the bitnami/kube-prometheus chart (see [#7690](https://github.com/bitnami/charts/issues/7690)),
      but differs from the behaviour of the upstream kube-state-metrics community chart.
  - For large production deployments (examples are based on a cluster with about 125 nodes and 7000 cores):
    - Increase `.Values.prometheus.querySpec.timeout` (e.g. ~ 1800s) to allow long queries to succeed.
    - Apply sufficient CPU and memory resource requests and limits.
  - If Prometheus is configured to require authentication, configure `.Values.processor.prometheus_auth` to specify an appropriate kubernetes
    secret containing authentication information.

Pods must specify CPU resource requests in order to be accounted. All pods in a specified namespace will be accounted.
To do accounting for different projects in multiple namespaces, a KAPEL chart can be installed and configured for each one.

## Configuration
- See [kube-prometheus-example.yaml](docs/kube-prometheus-example.yaml) for an example values file to use for installation of the Bitnami kube-prometheus Helm chart.
- See [values.yaml](chart/values.yaml) for the configurable values of the KAPEL Helm chart.
- See [KAPELConfig.py](python/KAPELConfig.py) for descriptions of the settings used in KAPEL.

## Helm chart installation
The KAPEL Helm chart is available from [this Helm repository](https://rptaylor.github.io/kapel/).

See the [Helm Chart README](chart/README.md) for additional information.
