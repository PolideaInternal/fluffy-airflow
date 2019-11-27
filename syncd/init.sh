#!/bin/bash
MAX_TIME_ELAPSED_VALUE=1000000
SQL_IP_SEARCH_FREQUENCY=60
KUBE_CREDENTIALS_REFRESH_FREQUENCY=3600 # 1 hour.
GCS_TENANT_BUCKET_EXISTS="FALSE"

# Timeout after 1h to prevent the extremely rare situation where gsutil process
# is stuck. Note that gsutil syncs 1000 objects at once with an average speed of
# O(10MBPS), 1h should be a very safe upper-bound.
GSUTIL_SYNC_TIMEOUT=60m
timeout_sync() {
  timeout --preserve-status -k 10 ${GSUTIL_SYNC_TIMEOUT} $@
}

gsutil_sync() {
  timeout_sync gsutil -m rsync -d -r "gs://${GCS_BUCKET}/dags" "${base_dir}/dags"
  timeout_sync gsutil -m rsync -d -r "gs://${GCS_BUCKET}/plugins" "${base_dir}/plugins"
}

tenant_bucket_exists() {
  if [[ "${GCS_TENANT_BUCKET_EXISTS}" != "TRUE" ]]; then
    timeout_sync gsutil ls "gs://${GCS_TENANT_BUCKET}" > /dev/null 2>&1
    if [[ $? -eq 0 ]]; then
      GCS_TENANT_BUCKET_EXISTS="TRUE"
    fi
  fi
  [[ "${GCS_TENANT_BUCKET_EXISTS}" == "TRUE" ]]
}

gsutil_sync_to_tenant() {
  if tenant_bucket_exists; then
    timeout_sync gsutil -m rsync -d -r "gs://${GCS_BUCKET}" "gs://${GCS_TENANT_BUCKET}"
  else
    echo "GCS tenant bucket is not available yet."
  fi
}


if [[ $# -ne 1 ]]; then
  echo "Usage: sync.sh airflow-local-base-dir"
  exit 1
fi
base_dir=$1
echo "Using base dir: ${base_dir}"
folders=("dags" "plugins")
# Create local directories if not exist.
for folder in "${folders[@]}"; do
  mkdir -p "${base_dir}/${folder}"
  if [[ $? -ne 0 ]]; then
    echo "Error creating local directory ${base_dir}/${folder}."
    exit 1
  fi
done

# rsync gcs bucket to local drive (and to tenant bucket, if configured)
echo "Syncing GCS bucket."
gsutil_sync
RES=$?

if [[ ! -z "${GCS_TENANT_BUCKET}" ]]; then
    echo "Syncing to GCS tenant bucket."
    gsutil_sync_to_tenant
    RES=$?
fi

exit "${RES}"
