#!/bin/bash

set -ex

VERSION=$(git describe --tags)

docker build -t repo.treescale.com/sorend/adpy:$VERSION .
