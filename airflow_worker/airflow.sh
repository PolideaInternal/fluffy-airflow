#!/bin/bash
# Copyright 2018 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

set -e

# Forwards command line arguments to airflow after mounting the GCS bucket
# and setting up GKE configuration files.
# Use by naming this script as the ENTRYPOINT in the Dockerfile,
# and in the Kubernetes container spec, provide an args field.
# e.g., args: ["scheduler"] will run "airflow scheduler"
# Temporarily add symbolic link to support default GKE 1.8.9 version with
# mount subPath bug.
if [ ! -L "/etc/airflow/airflow.cfg" ]; then
  ln -s "/etc/airflow/airflow_cfg/airflow.cfg" "/etc/airflow/airflow.cfg"
fi
mkdir -p /home/airflow/gcsfuse
gcsfuse --file-mode 755 --implicit-dirs --limit-ops-per-sec -1 \
    $GCS_BUCKET /home/airflow/gcsfuse
folders=("logs" "data")

# Create local directories if not exist.
for folder in "${folders[@]}"; do
  if [ ! -L "/home/airflow/gcs/${folder}" ]; then
    ln -s "/home/airflow/gcsfuse/${folder}" "/home/airflow/gcs/${folder}"
  fi
done

if [ -z "$AIRFLOW__CORE__SQL_ALCHEMY_CONN" ]; then
  while [ ! -f $SQL_PROXY_CONNECTION_STORE ]
  do
    echo "Waiting to find SQL Connection config file."
    sleep 5
  done
  echo "Found SQL Connection config file."
fi

# Setup Python command (PEP-394). No-op for Python2.
bash /var/local/setup_python_command.sh

if [ "$@" == "worker" ]; then
  RETRY=3
  until [ $RETRY -le 0 ]
  do
  # Use env variables to grab cluster credentials and update config file for
  # kubectl's access.
  # gcloud looks at KUBECONFIG environment variable to determine where to save
  # the configuration file. This is to potentially stop users from messing up
  # the default config. KubernetesPodOperator has the default location set
  # to '/home/airflow/composer_kube_config' as well to match this.
  export KUBECONFIG="/home/airflow/composer_kube_config"  &&
    /var/local/init_kube.sh &&
    break

  echo "Failed to get-credentials for ${COMPOSER_GKE_NAME}"
    RETRY=$[$RETRY - 1]
    # Sleep 5 seconds in case it was a transient error
    sleep 5
  done
  exec airflow "$@"
elif [ "$@" == "scheduler" ]; then
  while true; do
    airflow "$@" -r 600 # restarts every 600 seconds
    if [ $? -ne 0 ]; then
      echo "Found non-zero Airflow scheduler return-code."
      exit 1
    fi
    sleep 1
  done
elif [ "$@" == "webserver" ]; then
  exec airflow "$@"
else
  echo "Unexpected subcommand: $@"
  exit 1
fi
