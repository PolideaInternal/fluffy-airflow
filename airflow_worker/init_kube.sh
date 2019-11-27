#!/usr/bin/env bash
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

gcloud container clusters get-credentials ${GKE_NAME:=$COMPOSER_GKE_NAME} \
    --zone ${GKE_ZONE:=$COMPOSER_GKE_ZONE}
desc=$(gcloud container clusters describe ${GKE_NAME:=$COMPOSER_GKE_NAME} \
    --zone ${GKE_ZONE:=$COMPOSER_GKE_ZONE} --format=yaml)

# If this is a private cluster according to cluster.get and
# `endpoint` match `privateClusterConfig.publicEndpoint`,
# this cluster must be a private cluster with publicEndpoint, we need
# to replace the IP inside kube config file generated with privateEndpoint
# for pod to be able to talk to GKE master.
if [[ $desc =~ "enablePrivateNodes: true" ]]; then
  echo "Current cluster is a private cluster."
  # Match endpoint: (matched_group_until_space_or_eol)
  currentEndpoint=$(echo $desc | sed -n 's/.*endpoint: \([^ \\n]*\).*/\1/p')
  # Match privateEndpoint: (matched_group_until_space_or_eol)
  privateEndpoint=$(echo $desc | sed -n 's/.*privateEndpoint: \([^ \\n]*\).*/\1/p')
  # Match publicEndpoint: (matched_group_until_space_or_eol)
  publicEndpoint=$(echo $desc | sed -n 's/.*publicEndpoint: \([^ \\n]*\).*/\1/p')
  if [[ $currentEndpoint =~ $publicEndpoint ]]; then
    echo "Current cluster returns public endpoint $currentEndpoint."

    if [ -z "$KUBECONFIG" ]; then
      KUBECONFIG=$HOME/.kube/config
    fi

    echo "Replacing endpoint to $privateEndpoint in $KUBECONFIG."
    sed -i -e "s/${publicEndpoint}/${privateEndpoint}/g" $KUBECONFIG
  fi
fi
