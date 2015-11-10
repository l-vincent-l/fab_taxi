from __future__ import with_statement
import importlib
from fabric.api import *
from fabric.contrib.console import confirm

from fabtools import supervisor

from load_config import load_config
from machine import install_machine, restart_services, install_system
from geoserver import deploy_geoserver, restart_geotaxi
from api import deploy_api, upgrade_api, restart_api
from zupc import import_zupc
from dash import *
from env import env, load_config_dev
import logging
logging.basicConfig()


@task
def deploy():
    load_config()
    install_machine()
    deploy_geoserver()
    supervisor.update_config()
    restart_services()
    restart_geotaxi()
    deploy_api()
    upgrade_api()
