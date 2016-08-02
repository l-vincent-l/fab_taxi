from fabric.api import task, env
from fabric.operations import run, put
from fabtools import require, git, supervisor
from sqlalchemy.engine import url
from fabric.contrib import files
from fabric.context_managers import cd


def init_geotaxi():
    if not files.exists('GeoTaxi'):
        git.clone('https://github.com/openmaraude/GeoTaxi')
    install_geotaxi()
    require.files.directory('/var/log/geotaxi', use_sudo=True)
    put('files/geotaxi.conf', '/etc/rsyslog.d/geotaxi.conf', use_sudo=True)

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
    from .api import get_admin_key, install_admin_user
    install_admin_user()
    apikey = get_admin_key().splitlines()[0].strip()
    program = run('readlink -f GeoTaxi/geoloc-server')
    command='{} --port {} --fluentdip 0.0.0.0 --fluentdport 5160'.format(
        program, env.geoserver_port, )
    if env.geotaxi_authentication:
        command += ' --apikey {} --url {}'.format(apikey,
                               'https://'+env.server_name+'/users/')
    require.supervisor.process('geotaxi', command=command)

@task
def restart_geotaxi():
    supervisor.update_config()
    supervisor.restart_process('geotaxi')

@task
def deploy_geoserver():
    init_geotaxi()
    install_process_geotaxi()
    restart_geotaxi()
