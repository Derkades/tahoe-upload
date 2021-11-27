#!/bin/bash
set -ex
docker build -t derkades/tahoe-upload -f Dockerfile .
