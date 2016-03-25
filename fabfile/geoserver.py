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
    require.deb.packages(['libhiredis-dev'])
    git.checkout('GeoTaxi')
    git.pull('GeoTaxi')
    with cd('GeoTaxi'):
        require.files.directory('obj')
        run('make')

@task
def install_process_geotaxi():
    program = run('readlink -f GeoTaxi/geoloc-server')
    require.supervisor.process('geotaxi',
            command='{} {}'.format(program, env.geoserver_port))

@task
def restart_geotaxi():
    supervisor.update_config()
    supervisor.restart_process('geotaxi')

@task
def deploy_geoserver():
    init_geotaxi()
    install_process_geotaxi()
    restart_geotaxi()
