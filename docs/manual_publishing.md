# Procedure for publishing records manually

Sometimes it may be necessary to publish manually-defined records, instead of querying Prometheus to get accounting records.
There is a ConfigMap created by the Helm chart for this, which is named `kapel-manual-records` by default.
Manually edit that ConfigMap (e.g. `kubectl edit`) and insert the accounting information that you want to publish.
The keys of the ConfigMap are arbitrary and you can define as many as needed.
For example it could look like this:
```
apiVersion: v1
kind: ConfigMap
metadata:
  name: kapel-manual-records
  namespace: kapel
data:
  OctoberSummaryCorrection: |
    APEL-summary-job-message: v0.2
    Site: CA-EXAMPLE-T2
    Month: 10
    Year: 2022
    VO: atlas
    SubmitHost: k8s.example.org:6443/harvester
    InfrastructureType: grid
    ServiceLevelType: si2k
    ServiceLevel: 2975.0
    WallDuration: 188517
    CpuDuration: 188517
    NumberOfJobs: 383
    Processors: 0
    NodeCount: 0
    EarliestEndTime: 1664582401
    LatestEndTime: 1667260774
    %%
  OctoberSyncCorrection: |
    APEL-sync-message: v0.1
    Site: CA-EXAMPLE-T2
    SubmitHost: k8s.example.org:6443/harvester
    NumberOfJobs: 383
    Month: 10
    Year: 2022
    %%
```

Then wait for the next scheduled CronJob run to publish the records, or manually create a Job from the CronJob.
Afterwards, __you must remove all contents and keys of the data field__ of the ConfigMap in order to return to the normal querying mode.
Note that upgrading the Helm chart will erase any manually-defined records and reset this ConfigMap to the default empty state, for normal operation.
