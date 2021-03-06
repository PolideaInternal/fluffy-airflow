#!/bin/bash

set -ex

version="ver-${RANDOM}"
image="eu.gcr.io/polidea-airflow/gcs-syncd:${version}"
echo ${version}
docker build . -t "${image}"
docker push "${image}"
echo ${image}