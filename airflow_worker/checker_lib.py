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
"""Utility functions that facilitate worker and scheduler liveness checker."""

from datetime import datetime
from datetime import timedelta
from six import iteritems
import socket

from airflow import models
from airflow.settings import Session
from sqlalchemy import func

host_name = socket.gethostname()


def _check_query_size(task_query):
  query_statement = task_query.statement.with_only_columns([func.count()])
  return task_query.session.execute(query_statement).scalar()


def task_count_by_state(use_host_name=True):
  ten_minutes_ago = datetime.utcnow() - timedelta(minutes=10)
  try:
    from airflow.utils import timezone
    ten_minutes_ago = timezone.utcnow() - timedelta(minutes=10)
  except:
    pass
  queries = {
      state: Session.query(
          models.TaskInstance).filter(models.TaskInstance.state == state)
      for state in ('scheduled', 'queued', 'running')
  }
  queries['recently_done'] = Session.query(models.TaskInstance).filter(
      models.TaskInstance.state.in_(['success', 'failed', 'up_for_retry']),
      models.TaskInstance.end_date > ten_minutes_ago)

  if use_host_name:
    for state in ('running', 'recently_done'):
      queries[state] = queries[state].filter(
          models.TaskInstance.hostname == host_name)

  return {state: _check_query_size(query)
          for state, query in iteritems(queries)}


def declare_error_state(task_counts, check_scheduled=False):
  return ((task_counts['queued'] > 0
           or (check_scheduled and task_counts['scheduled'] > 0))
          and task_counts['running'] == 0 and task_counts['recently_done'] == 0)
