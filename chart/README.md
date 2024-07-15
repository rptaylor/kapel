# Kuantifier Helm Chart

Kuantifier is installed and configured via a Helm chart. You must [install helm](https://helm.sh/docs/intro/install/) prior to 
configuring and installing Kuantifier in your Kubernetes cluster.

## Installation
The Kuantifier Helm Chart is hosted at the OSG Harbor [OCI registry](https://helm.sh/docs/topics/registries/). To find the latest version of 
the Kuantifier helm chart:
    
    helm show chart oci://hub.opensciencegrid.org/iris-hep/kuantifier

Then [install](https://helm.sh/docs/helm/helm_install/) it:

    helm install kuantifier oci://hub.opensciencegrid.org/iris-hep/kuantifier --version <latest-version> --values my-values.yaml

Or [upgrade](https://helm.sh/docs/helm/helm_upgrade/) an existing installation with a new helm chart version or set of configuration values:

    helm upgrade kuantifier oci://hub.opensciencegrid.org/iris-hep/kuantifier --version <latest-version> --values my-values.yaml

## Configuration

Helm charts are configured via a YAML [configuration file](https://helm.sh/docs/chart_template_guide/values_files/). The default
configuration for Kuantifier is found at [values.yaml](./values.yaml). A custom values.yaml may be applied to a chart during
installation or upgrade via the `--values` or `-f` helm command line option. The parameters of Kuantifier's values.yaml are documented
below.

### Values.yaml Parameters

#### General Configuration
* `.Values.outputFormat`: The outlet to report records to. Supports two values:
  * `"ssmsend"`: Output to APEL via SSM.
  * `"gratia"`: Output to [GRACC](https://gracc.opensciencegrid.org/) via 
    [Gratia](https://github.com/opensciencegrid/gratia-probe/).
* `.Values.cronjob`: Configuration for the Kubernetes [CronJob](https://kubernetes.io/docs/concepts/workloads/controllers/cron-jobs/)
  object that periodically runs Kuantifier.
  * `.schedule`: Cron expression for scheduling the CronJob.
  * `.priorityClassName`: [Priority Class](https://kubernetes.io/docs/concepts/scheduling-eviction/pod-priority-preemption/) for the
    pods that run the Kuantifier job.
  * `.ttlSecondsAfterFinished`: Duration to persist completed pods after completion. 
* `.Values.pspName`: If specified, a [Pod Security Policy](https://kubernetes.io/docs/concepts/security/pod-security-policy/)
    name to use. Deprecated in newer versions of Kubernetes.
* `.Values.user`: Can be used to change the [user id and group id](https://kubernetes.io/docs/tasks/configure-pod-container/security-context/) the pod runs as if needed.

* `.Values.dataVolumeSize`: The size of the volume where Kuantifier stores its intermediate results between querying Prometheus
  and outputting to an external service. Note that Gratia output may require a significantly larger data volume size, as it operates
  on non-summarized records.

* `.Values.processor`: Configuration for the container that queries Prometheus to generate Job metric records.
  * `.image_repository`: OCI image repository from which to pull the processor image.
  * `.image_tag`: Optionally specify an image version.
  * `.image_pull_policy`: [Image Pull Policy](https://kubernetes.io/docs/concepts/containers/images/#image-pull-policy) for the processor container.
  * `.resources`: [Resource requests and limits](https://kubernetes.io/docs/concepts/configuration/manage-resources-containers/) for
   the processor container. Allow approximately 10KB of memory per job record being processed.
  * `.config`: Environment variables for the processor. See [KAPELConfig.py](../python/KAPELConfig.py) for full details. 
  Must specify at least the following sub-fields:
    * `.namespace`: The namespace of the pods for which Kuantifier will collect and report metrics.
    * `.siteName`: The name of the site being reported.
    * `.submitHost`: Uniquely identifying name for the cluster.
    * `.voName`: VO of jobs.
  * `.prometheus`: Config for connecting to your cluster's Prometheus instance. Has the following sub-fields:
    * `.server`: Required. URL of your cluster's prometheus server.
    * `.auth.secret`: Optional. If your Prometheus instance is configured to require [Authentication](https://prometheus.io/docs/prometheus/latest/configuration/https/) from within the cluster, 
    specify a Secret containing a value for the authentication header.
    * `.auth.key`: Optional. If using a secret for authentication, which key within the secret to use as the auth header.
 
#### Gratia Output Configuration

The following values only apply if `.Values.outputFormat` equals `"gratia"`:

* `.Values.gratia`: Configuration for the container that outputs job records to GRACC.
  * `.image_repository`: OCI image repository from which to pull the Gratia output image.
  * `.image_tag`: Optionally specify an image version.
  * `.resources`: Resource requests and limits for the Gratia output container.
  * `.config`: Environment variables for the Gratia output container. Currently, it is strongly recommended to use the default.

#### SSMSend Output Configuration

The following values only apply if `.Values.outputFormat` equals `"ssmsend"`:

* `.Values.ssmsend`: Configuration for the container that outputs job records to APEL.
  * `.image_repository`: OCI image repository from which to pull the SSM output image.
  * `.image_tag`: Optionally specify an image version.
  * `.resources`: Resource requests and limits for the SSM output container.
  * `.x509cert` and `.x509key`: Base64-encoded public cert and private key for content signing when sending messages with SSM for APEL.
  * `.config`: Environment variables for the processor that determine ssmsend-specific behavior. Sub-fields include:
    * `.benchmarkValue`: Required: The value to use for normalizing by CPU performance.
    * `.nodeCount`: Optional: Number of nodes the report summarizes over.
    * `.processors`: Optional: Number of processors the report summarizes over.
