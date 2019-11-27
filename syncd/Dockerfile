FROM eu.gcr.io/cloud-airflow-releaser/gcs-syncd:latest

RUN sudo wget -O /usr/local/bin/dumb-init https://github.com/Yelp/dumb-init/releases/download/v1.2.1/dumb-init_1.2.1_amd64 && \
echo "057ecd4ac1d3c3be31f82fc0848bf77b1326a975b4f8423fe31607205a0fe945  /usr/local/bin/dumb-init" | sha256sum -c - && \
sudo chmod 755 /usr/local/bin/dumb-init

ENTRYPOINT ["/usr/local/bin/dumb-init", "--", "/home/airflow/sync.sh"]
