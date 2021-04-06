#!/bin/bash

buildah bud --squash -t ssmsend https://raw.githubusercontent.com/rptaylor/kapel/master/ssmsend-build/Dockerfile
