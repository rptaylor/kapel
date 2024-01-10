- https://hub.docker.com/_/python
- https://hub.docker.com/_/centos
- https://kubernetes.io/docs/tasks/job/automated-tasks-with-cron-jobs/#concurrency-policy
- https://kubernetes.io/docs/tasks/job/automated-tasks-with-cron-jobs/#jobs-history-limits

# Build and push ssmsend container
```
registry=<example.org>  # e.g. "git.computecanada.ca:4567/rptaylor/misc"
tag=<X.Y.Z>             # e.g. "3.3.1"

buildah bud --squash -t ssmsend https://raw.githubusercontent.com/rptaylor/kapel/master/ssmsend-build/Containerfile
imageid=`buildah images --format '{{.ID}}' ssmsend`
buildah login $registry
buildah push $imageid $registry/ssmsend:$tag
```

# Build and publish Helm chart to repository
```
helm package chart/
helm repo index --url  https://rptaylor.github.io/kapel/  .
```
