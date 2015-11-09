from fabric.api import task, env, settings, sudo
from fabric.operations import run, put, sudo
from fabtools import require, supervisor
from sqlalchemy.engine import url
from fabric.contrib import files
from fabric.context_managers import cd
import re


def install_system():
    run('su root -c "apt-get --force-yes install sudo && adduser {} sudo"'.format(env.user))
    require.deb.uptodate_index()
    sudo('apt-get --force-yes upgrade')
    require.system.locale(env.postgres_locale)
    require.files.directory(env.wwwdata_logdir, owner='www-data', group='adm')
    require.files.directory(env.wwwdata_piddir, owner='www-data', group='adm')


def install_postgres_postgis():
    require.postgres.server()
    u = url.make_url(env.conf_api.SQLALCHEMY_DATABASE_URI)
    require.postgres.user(u.username, u.password)
    require.postgres.database(u.database, owner=u.username, locale=env.postgres_locale)
    with settings(sudo_user='postgres'):
        sudo('psql -c "CREATE EXTENSION IF NOT EXISTS postgis;" --dbname={}'\
                .format(u.database))


def install_dependencies():
    require.deb.uptodate_index()
    require.deb.packages(['autoconf-archive', 'automake-1.14', 'autoconf2.59',
        'build-essential', 'check', 'libspatialindex-dev', 'git',
        'libgcrypt11-dev', 'unzip', 'cmake', 'libpq-dev', 'python2.7-dev',
        'supervisor', 'locales', 'postgis', 'curl', 'libpcre3', 'libpcre3-dev'])
    install_postgres_postgis()
    require.nginx.server()

def add_users():
         require.users.user('taxis')

def install_krmt():
    if files.exists('krmt/geo.so'):
        return
    run('wget https://github.com/mattsta/krmt/archive/master.zip -O krmt.zip')
    run('unzip krmt.zip')
    run('rm krmt.zip')
    run('mv krmt-master krmt')
    with cd('krmt'):
        run('make')


def install_yajl():
    if files.exists('yajl/build/yajl-*/bin/json_reformat'):
        return
    run('wget https://github.com/lloyd/yajl/archive/master.zip -O yajl.zip')
    run('unzip yajl.zip')
    run('mv yajl-master yajl')
    run('rm yajl.zip')
    with cd('yajl'):
        run('./configure')
        run('make')


def install_redis():
    if files.exists('redis/src/redis-server'):
        return
    run('wget https://github.com/mattsta/redis/archive/dynamic-redis-2.8.zip')
    run('unzip dynamic-redis-2.8.zip')
    run('rm dynamic-redis-2.8.zip')
    run('mv redis-dynamic-redis-2.8 redis')
    with cd('redis'):
        run('make')
        sudo('cp src/redis-server /usr/bin/redis-server')
        sudo('chown {0}:{0} /usr/bin/redis-server'.format(env.user))


def install_services():
    install_redis()
    install_yajl()
    install_krmt()
    if not files.exists('/var/run/supervisor.sock'):
        sudo('supervisord -c /etc/supervisor/supervisord.conf')
    supervisor.reload_config()


@task
def restart_services():
    geoso = run('readlink -f krmt/geo.so')
    command = 'redis-server --module-add {} '.format(geoso)
    if 'redis_conf' in env.__dict__.keys():
        put(env.local_redis_conf, 'redis/redis.conf')
        redis_conf = run('readlink -f redis/redis.conf')
        command += ' {}'.format(redis_conf)
    else:
        redis_port = re.search(r'redis://.*:.*@*.:(\d+)', env.conf_api.REDIS_URL).group(1)
        command += ' --port {}'.format(redis_port)
    require.files.directory('/var/log/redis', use_sudo=True, owner=env.user)
    require.files.file('/var/log/redis/error.log', owner=env.user)
    require.supervisor.process('redis', command=command,
            stdout_logfile='/var/log/redis/error.log')


@task
def install_machine():
    install_dependencies()
    add_users()
    install_services()
