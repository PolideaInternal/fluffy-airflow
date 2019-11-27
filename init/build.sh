#!/bin/bash

set -ex

version="ver-${RANDOM}"
image="eu.gcr.io/polidea-airflow/worker_init:${version}"
echo ${version}
docker build . -t "${image}"
docker push "${image}"
echo ${image}