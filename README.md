# kapel
APEL accounting for Kubernetes.

## Requirements
- kube-state-metrics and Prometheus ([bitnami/kube-prometheus](https://bitnami.com/stack/prometheus-operator/helm) is recommended)
- X509 host certificate and key for publishing APEL records with ssmsend
- ssmsend container built using the provided Dockerfile
