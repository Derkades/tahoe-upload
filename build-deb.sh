#!/bin/bash
set -ex
docker build -t tahoe-upload-deb-builder -f Dockerfile.deb-build --build-arg UID=$(id -u) --build-arg GID=$(id -g) .
ID=$(docker create tahoe-upload-deb-builder)
docker cp "$ID:/data/debs/." .
docker rm -v $ID
