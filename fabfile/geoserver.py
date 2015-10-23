from fabric.api import task, env
from fabric.operations import run
from fabtools import require, git, supervisor
from sqlalchemy.engine import url
from fabric.contrib import files
from fabric.context_managers import cd


def init_geotaxi():
    if not files.exists('GeoTaxi'):
        git.clone('https://github.com/openmaraude/GeoTaxi')
    install_geotaxi()

@task
def install_geotaxi():
    git.pull('GeoTaxi')
    with cd('GeoTaxi/src'):
        require.files.directory('obj')
        run('make')

@task
def restart_geotaxi():
    program = run('readlink -f GeoTaxi/src/geoloc-server')
    require.supervisor.process('geotaxi',
            command='{} {}'.format(program, env.geoserver_port))


@task
def deploy_geoserver():
    init_geotaxi()
