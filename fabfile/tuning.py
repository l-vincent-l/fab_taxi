from fabric.api import task, env, settings, sudo
from fabric.operations import run, put, sudo, prompt
from fabtools import require, supervisor
from sqlalchemy.engine import url
from fabric.contrib import files
from fabric.context_managers import cd
import re

@task
def tune_system():
    sudo('sysctl -w net.core.somaxconn={}'.format(env.somaxconn))
    sudo('sysctl -w net.ipv4.tcp_max_syn_backlog={}'.format(env.tcp_max_syn_backlog))
    sudo('grep net.core.somaxconn /etc/sysctl.conf '
            '|| echo "net.core.somaxconn = {}" >> /etc/sysctl.conf'.format(env.somaxconn))
    sudo('grep net.ipv4.tcp_max_syn_backlog /etc/sysctl.conf '
            '|| echo "net.ipv4.tcp_max_syn_backlog = {}" >> /etc/sysctl.conf'.format(env.tcp_max_syn_backlog))
