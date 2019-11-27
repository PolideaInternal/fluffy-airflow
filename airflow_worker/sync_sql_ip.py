"""Library to update the Airflow SQLProxy Service with a valid SQL connection.

This module can be executed from the command-line or the classes can be used
independently.

  Typical usage example:

  python sync_sql_ip.py
      --cidr $SQL_SUBNET \
      --sql_database $SQL_DATABASE \
      --sql_user $SQL_USER \
      --sql_password $SQL_PASSWORD

  Given the SQL Subnet and the credentials, this program will
  find the valid IP address of the SQL instance and update the
  "airflow-sqlproxy-service".
"""

from ipaddress import ip_network
import sqlalchemy
from sqlalchemy import create_engine
import argparse
import logging
from kubernetes import client as k8s_client, config as k8s_config

CONNECT_TIMEOUT = 2
AIRFLOW_SQLPROXY_SERVICE_NAME = "airflow-sqlproxy-service"
# This template needs to be formatted with the user, password, address, and
# database in that order.
SQL_ALCHEMY_CONN_TEMPLATE = "mysql+mysqldb://{}:{}@{}/{}"


class SqlCredentials(object):
  """Object that contains the credentials for a SQL database.

  Attributes:
    sql_database: The database name
    sql_user: The username for the SQL instance.
    sql_password: The password for the SQL instance.
  """

  def __init__(self, sql_database=None, sql_user=None, sql_password=None):
    """Instantiates the SqlCredentials"""
    self.sql_database = sql_database
    self.sql_user = sql_user
    self.sql_password = sql_password


class SqlConnectionUtils(object):
  """Utility object that finds SQL connections and updates the SQL Proxy Service.

  Attributes:
    credentials: A SqlCredentials object for the target SQL instance.
  """

  def __init__(self, credentials):
    """Instantiates the SqlConnectionUtils with credentials"""
    self.credentials = credentials

  def create_db_conn_string(self, address):
    """Creates a SQL Alchemy connection string with a given IP Address"""
    return SQL_ALCHEMY_CONN_TEMPLATE.format(self.credentials.sql_user,
                                            self.credentials.sql_password,
                                            address,
                                            self.credentials.sql_database)

  def _test_connection(self, conn):
    engine = create_engine(
        conn, connect_args={"connect_timeout": CONNECT_TIMEOUT})
    try:
      connection = engine.connect()
      connection.close()
      return True
    except sqlalchemy.exc.OperationalError:
      return False

  def find_working_ip_address(self, cidr_block):
    """Finds a working IP address for the SQL instance."""
    ip_range = ip_network(unicode(cidr_block))
    for address in ip_range:
      logging.info("Testing SQL connection for IP {}.".format(address))
      conn = self.create_db_conn_string(address)
      if self._test_connection(conn):
        return str(address)

  def find_working_connection(self, cidr_block):
    """Finds a working SQL Alchemy connection for the SQL instance."""
    address = self.find_working_ip_address(cidr_block)
    if address:
      return self.create_db_conn_string(address)

  def update_sql_ip_address(self, ip_address):
    """Updates the SQL Proxy service with the new IP address."""
    k8s_config.load_kube_config()
    k8s_api = k8s_client.CoreV1Api()
    k8s_api.patch_namespaced_service(
        AIRFLOW_SQLPROXY_SERVICE_NAME,
        "default",
        body=self._get_body_for_service_update(ip_address))

  def _get_body_for_service_update(self, ip_address):
    body = k8s_client.V1Service(kind="Service", api_version="v1")
    body.metadata = k8s_client.V1ObjectMeta(
        name=AIRFLOW_SQLPROXY_SERVICE_NAME,
        namespace="default",
    )
    body.spec = k8s_client.V1ServiceSpec(
        type="ExternalName",
        external_name=ip_address)
    return body


def main():
  parser = argparse.ArgumentParser(
      description="Given a CIDR block, it will find the IP Address within the "
      "block that has a valid SQL proxy running on it.")
  parser.add_argument(
      "--cidr",
      help="The CIDR block where the SQL proxy "
      "instance exists on.",
      nargs=1,
      required=True)
  parser.add_argument(
      "--sql_database", help="The SQL database name.", nargs=1, required=True)
  parser.add_argument(
      "--sql_user",
      help="The SQL user for the instance.",
      nargs=1,
      required=True)
  parser.add_argument(
      "--sql_password", help="The SQL user's password.", nargs=1, required=True)
  args = parser.parse_args()

  cidr_block = args.cidr[0]
  credentials = SqlCredentials(
      sql_database=args.sql_database[0],
      sql_user=args.sql_user[0],
      sql_password=args.sql_password[0])
  utils = SqlConnectionUtils(credentials)
  ip_address = utils.find_working_ip_address(cidr_block)
  if ip_address:
    utils.update_sql_ip_address(ip_address)
  else:
    logging.error("Could not find valid SQL connection in provided subnet")


if __name__ == "__main__":
  main()
