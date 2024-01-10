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
- First remember to update Chart.yaml with a new version (potentially appVersion too)
- Copy the chart dir out of the git repo
- `git checkout gh-pages`
- Move the chart dir into the git repo
- `helm package chart/`
- `rm -rf chart/`
- `helm repo index .`
- git add, commit, push
