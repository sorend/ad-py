#!/bin/bash

set -ex

VERSION=$(git describe --tags)

# push release
echo $HUB_PASSWORD | docker login --username $HUB_USERNAME --password-stdin repo.treescale.com
docker push repo.treescale.com/sorend/adpy:$VERSION

# poor mans templating
cat k8s.yml | sed -e "s/VERSION/$VERSION/g" > k8s-versioned.yml
cat k8s-versioned.yml

# deploy
KUBECONFIG=./kubeconfig kubectl apply -f adpy-secret.yml -n default
KUBECONFIG=./kubeconfig kubectl apply -f k8s-versioned.yml -n default
