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
# Initializes the Airflow db, setting up the Python environment
# beforehand so that pickling is done correctly.
#
# Wrapper to run program with injected AIRFLOW connection env or use
# original env as is if no SQL_SUBNET is provided and AIRFLOW connection
# env already exists.

import time
import subprocess, os
import sys

RETRY_COUNT = 3
AIRFLOW_CONNECTION_ENV_KEY = "AIRFLOW__CORE__SQL_ALCHEMY_CONN"

def _generate_env():
  sql_net = os.getenv("SQL_SUBNET")
  sql_con = os.getenv(AIRFLOW_CONNECTION_ENV_KEY)

  db_env = os.environ.copy()
  if sql_net is None:
    if sql_con is None:
      raise Exception("Can not found SQL_SUBNET env variable.")
    else:
      return db_env

  import sync_sql_ip

  start_t = time.time()

  con = None
  i = 0
  while con is None and i < RETRY_COUNT:
    sql_conn_utils = sync_sql_ip.SqlConnectionUtils(
        sync_sql_ip.SqlCredentials(
            sql_database=db_env["SQL_DATABASE"],
            sql_user=db_env["SQL_USER"],
            sql_password=db_env["SQL_PASSWORD"]))
    con = sql_conn_utils.find_working_connection(sql_net)
    if con is None:
      time.sleep(90)
      i += 1

  if con is None:
    raise Exception("Can not connect to airflow database.")

  delta_t = time.time() - start_t
  print("Connect to DB after {:.3f} seconds".format(delta_t))

  db_env[AIRFLOW_CONNECTION_ENV_KEY] = con
  return db_env

if __name__ == "__main__":
  db_env = _generate_env()
  if len(sys.argv) > 1:
    subprocess.check_call(sys.argv[1:], env=db_env, shell=False)
