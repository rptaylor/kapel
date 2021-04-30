#!/bin/bash

# registry=
# tag=

buildah bud --squash -t ssmsend https://raw.githubusercontent.com/rptaylor/kapel/master/ssmsend-build/Containerfile
imageid=`buildah images --format '{{.ID}}' ssmsend`
buildah login $registry
buildah push $imageid $registry/ssmsend:$tag
