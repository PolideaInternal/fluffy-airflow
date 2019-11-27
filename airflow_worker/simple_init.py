#!/usr/bin/env python
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
"""Initializes the Airflow deployment.

Namely, does the following:
  * Sets up tables in the Airflow database.
  * Initializes GCP-related Airflow Connections so that their project
    fields point to the GCP project in which the Airflow deployment was
    created. Creates any missing connections.
"""
# Import subprocess and fix symlink to airflow configs before airflow modules
# are imported.
import subprocess


def _symlink_airflow_cfg():
  """Creates symbolic link to airflow.cfg in /etc/airflow.

  Temporarily add symbolic link to support default GKE 1.8.9 version with
  mount subPath bug.
  """
  subprocess.check_call([
      'ln', '-sf', '/etc/airflow/airflow_cfg/airflow.cfg',
      '/etc/airflow/airflow.cfg'
  ])


_symlink_airflow_cfg()

import json
import os

from airflow import models
from airflow import settings

GCS_BUCKET_ENV = 'GCS_BUCKET'
GCP_PROJECT_ENV = 'GCP_PROJECT'
CONNECTION_PROJECT_EXTRA_KEY = 'extra__google_cloud_platform__project'
GCP_CONN_IDS = ['google_cloud_default',
                'bigquery_default',
                'google_cloud_datastore_default',
                'google_cloud_storage_default']

def _init_airflow_db():
  """Initializes Airflow database."""
  subprocess.call(['airflow', 'initdb'])


def _init_gcs_directories(bucket):
  """Creates GCS bucket subdirectories."""
  # we check the existence of ../data first before mounting the gcs bucket and
  # creating sub-directories, this allow simple_init script to be called
  # anytime.
  if not os.path.exists('/home/airflow/gcs/data'):
    subprocess.call(['gcsfuse', bucket, '/home/airflow/gcs'])
    subprocess.call(['mkdir', '-p', '/home/airflow/gcs/dags'])
    subprocess.call(['mkdir', '-p', '/home/airflow/gcs/data'])
    subprocess.call(['mkdir', '-p', '/home/airflow/gcs/logs'])
    subprocess.call(['mkdir', '-p', '/home/airflow/gcs/plugins'])


def _init_conn_id(session, conn_id, project):
  """Initializes the GCP project extra field of Airflow Connections.

  Airflow allows multiple Connections to share the same conn_id field.
  This function sets the GCP project field in the extras field of all
  Connections with a certain conn_id.

  If no Connection exists with the given conn_id, creates one and sets
  its project field.

  :param session: the DB session
  :type session: sqlalchemy.orm.session.Session
  :param conn_id: the conn_id of connections to modify
  :type conn_id: string
  :param project: the project name or ID to associate with the
      connection(s)
  :type project: string
  """

  num_conns = 0
  for conn in (session.query(
      models.Connection).filter(models.Connection.conn_id == conn_id)):
    num_conns += 1
    extras = conn.extra_dejson
    extras[CONNECTION_PROJECT_EXTRA_KEY] = project
    conn.extra = json.dumps(extras)

  if not num_conns:
    extras = json.dumps({CONNECTION_PROJECT_EXTRA_KEY: project})
    conn = models.Connection(
        conn_id=conn_id, conn_type='google_cloud_platform', extra=extras)
    session.add(conn)


def _init_connections(session, conn_ids, project):
  """Sets the project extra field in GCP-related Airflow Connections.

  Creates a Connection with the given project field for conn_id's
  that do not already have a corresponding connection.

  :param session: the DB session
  :type session: sqlalchemy.orm.session.Session
  :param conn_ids: the conn_id's of connections to modify
  :type conn_ids: list of strings
  :param project: the project name or ID to associate with the
      connection
  :type project: string
  """
  for conn_id in conn_ids:
    _init_conn_id(session, conn_id, project)


def _update_airflow_db_connection(session):
  """Updates airflow_db connection to contain the proper host and schema.

  Updates airflow_db connection to contain the airflow-sqlproxy-service's
  namespace-qualified host name as host and the current DB as the schema. If the
  airflow_db connection does not exist, it creates one.

  :param session: the DB session
  :type session: sqlalchemy.orm.session.Session
  """
  airflow_db_conn = (
      session.query(models.Connection).filter(
          models.Connection.conn_id == 'airflow_db').first())
  if not airflow_db_conn:
    airflow_db_conn = models.Connection(
        conn_id='airflow_db', conn_type='mysql', login='root',
        password=os.environ.get('SQL_PASSWORD'))
    session.add(airflow_db_conn)
  else:
    airflow_db_conn.password = os.environ.get('SQL_PASSWORD')
  airflow_db_conn.host = 'airflow-sqlproxy-service.default'
  airflow_db_conn.schema = os.environ.get('SQL_DATABASE')


def main():
  _init_airflow_db()
  _init_gcs_directories(os.getenv(GCS_BUCKET_ENV))

  session = settings.Session()
  try:
    _init_connections(session, GCP_CONN_IDS, os.getenv(GCP_PROJECT_ENV))
    _update_airflow_db_connection(session)
    session.commit()
  except:
    session.rollback()
    raise
  finally:
    session.close()


if __name__ == '__main__':
  main()
