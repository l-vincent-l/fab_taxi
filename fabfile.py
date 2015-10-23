from __future__ import with_statement
import importlib
from fabric.api import *
from fabric.contrib.console import confirm

from .load_config import load_config
from .machine import install_machine
from .geoserver import deploy_geoserver
from .api import deploy_api

@task
def deploy():
    load_config()
    install_machine()
    deploy_geoserver()
    deploy_api()

