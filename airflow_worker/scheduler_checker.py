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
"""Airflow scheduler liveness probe.

The check logic concludes that a scheduler is in bad state if:
  - number of queued/scheduled tasks > 0 (tasks waiting to be processed).
  - number of running tasks == 0 (no work has been assigned).
  - number of recently completed task is 0.
In addition, the liveness prober also queries the timestamp of airflow scheduler
stackdriver logs. If the timestamp is too old, the probe is deemed failed.
"""

import argparse
import datetime
import os
from subprocess import PIPE
from subprocess import Popen
from subprocess import STDOUT
import sys

import iso8601

from google.cloud import logging_v2

GCP_PROJECT = 'GCP_PROJECT'
COMPOSER_LOCATION = 'COMPOSER_LOCATION'
COMPOSER_ENVIRONMENT = 'COMPOSER_ENVIRONMENT'


def _check_env_vars():
  """Exits if any required environment variables are missing."""
  env_vars = [GCP_PROJECT, COMPOSER_LOCATION, COMPOSER_ENVIRONMENT]
  missing = ', '.join(v for v in env_vars if os.environ.get(v) is None)
  if missing:
    sys.exit('Missing environment variable(s): %s' % missing)


def _is_log_ingestion_disabled():
  """Determines heuristically whether or not log ingestion is disabled.

  Returns True iff we are able to retrieve a logging exclusion named
  'google-ui-logs-ingestion-off' that is not disabled.
  """
  client = logging_v2.ConfigServiceV2Client()
  exclusion_name = client.exclusion_path(os.environ.get(GCP_PROJECT),
                                         'google-ui-logs-ingestion-off')
  try:
    exclusion = client.get_exclusion(exclusion_name)
    return not exclusion.disabled
  except:
    return False


def _get_log_filter():
  format_string = 'resource.type="cloud_composer_environment" AND ' + \
      'resource.labels.location="{}" AND ' + \
      'resource.labels.environment_name="{}" AND ' + \
      'logName="projects/{}/logs/airflow-scheduler" ' + \
      '"jobs.py"'
  return format_string.format(
      os.environ.get(COMPOSER_LOCATION), os.environ.get(COMPOSER_ENVIRONMENT),
      os.environ.get(GCP_PROJECT))


def check_freshness(args):
  _check_env_vars()
  if _is_log_ingestion_disabled():
    return
  filter_string = _get_log_filter()
  p = Popen(
      [
          'gcloud', 'logging', 'read', filter_string, '--limit', '1',
          '--format', 'get(timestamp)', '--project',
          os.environ.get(GCP_PROJECT)
      ],
      stdout=PIPE,
      stderr=STDOUT)
  (res, _) = p.communicate()
  # Only check Stackdriver freshness if there was a result, and the call
  # succeeded.
  if res and not p.returncode:
    try:
      dt = iso8601.parse_date(res)
    except iso8601.iso8601.ParseError:
      # Python3-compatibility
      dt = iso8601.parse_date(res.decode('UTF-8'))

    # If the log entry is 300 seconds old, we consider that the scheduler is
    # temporarily down.
    if (datetime.datetime.utcnow() -
        dt.replace(tzinfo=None)).seconds > args['staleness']:
      exit(1)


def main():
  # Skip the check if composer stackdriver is disabled.
  parser = argparse.ArgumentParser()
  parser.add_argument(
      '-s',
      '--staleness',
      type=int,
      default=300,
      help='Age threshold when a log entry is considered staled.')
  check_freshness(vars(parser.parse_args()))

  # import before use so airflow installation is not needed to run the test.
  import checker_lib
  task_counts = checker_lib.task_count_by_state(False)
  print('Task count details: {}'.format(task_counts))
  if checker_lib.declare_error_state(task_counts, check_scheduled=True):
    raise Exception('Scheduler seems to be dead.')


if __name__ == '__main__':
  main()
