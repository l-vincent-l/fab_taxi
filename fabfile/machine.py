from fabric.api import task, env, settings, sudo
from fabric.operations import run, put, sudo, prompt
from fabtools import require, supervisor
from sqlalchemy.engine import url
from fabric.contrib import files
from fabric.context_managers import cd
import re

@task
def install_system():
    deploy_user = env.user
    env.user = 'root'
    require.deb.package('sudo')
    password = prompt('{} password:'.format(deploy_user))
    require.users.user(deploy_user, password=password)
    require.users.sudoer(deploy_user)
    require.deb.uptodate_index()
    run('apt-get --force-yes upgrade')
    require.system.locale(env.postgres_locale)
    require.files.directory(env.uwsgi_logdir, owner='www-data', group='adm',
            use_sudo=True)
    require.files.directory(env.uwsgi_launcher_logdir, owner='www-data', group='adm',
            use_sudo=True)
    require.files.directory(env.uwsgi_pid_dir, owner='www-data', group='adm',
            use_sudo=True)
    require.files.directory(env.uwsgi_socket_dir, owner='www-data', group='adm',
            use_sudo=True)
    require.files.directory(env.uwsgi_dir, owner=deploy_user,
            use_sudo=True)
    require.files.directory('/var/log/celery', owner='www-data', group='adm',
            use_sudo=True)
    env.user = deploy_user


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
        'supervisor', 'locales', 'postgis', 'curl', 'libpcre3', 'libpcre3-dev',
        'unzip','munin', 'libgeos-dev', 'libjpeg62-turbo-dev',
        'libfreetype6', 'libfreetype6-dev'])
    install_postgres_postgis()
    require.nginx.server()

def add_users():
         require.users.user('taxis')

def install_krmt():
    if files.exists('/usr/lib/krmt/geo.so'):
        return
    with cd('/tmp'):
        run('wget https://github.com/mattsta/krmt/archive/master.zip -O krmt.zip')
        run('unzip krmt.zip')
        run('rm krmt.zip')
        run('mv krmt-master krmt')
        with cd('krmt'):
            run('make')
        require.files.directory('/usr/lib/krmt', use_sudo=True)
        sudo('mv krmt/*so /usr/lib/krmt')
        run('rm -rf yajl krmt')


def install_yajl():
    run('wget https://github.com/lloyd/yajl/archive/master.zip -O yajl.zip')
    run('unzip yajl.zip')
    run('mv yajl-master yajl')
    run('rm yajl.zip')
    with cd('yajl'):
        run('./configure')
        run('make')


def install_redis():
    if files.exists('/usr/bin/redis-server'):
        print 'Redis is already installed'
        return
    with cd('/tmp/'):
        install_yajl()
        run('wget https://github.com/mattsta/redis/archive/dynamic-redis-2.8.zip')
        run('unzip dynamic-redis-2.8.zip')
        run('rm dynamic-redis-2.8.zip')
        run('mv redis-dynamic-redis-2.8 redis')
        with cd('redis'):
            run('make')
            sudo('cp src/redis-server /usr/bin/redis-server')
            sudo('chown {0}:{0} /usr/bin/redis-server'.format(env.user))
            sudo('cp src/redis-cli /usr/bin/redis-cli')
            sudo('chown {0}:{0} /usr/bin/redis-cli'.format(env.user))

def install_services():
    install_redis()
    install_krmt()
    run('rm -rf /tmp/redis')
    if not files.exists('/etc/redis.conf'):
        put('files/redis.conf', '/etc/', use_sudo=True)
    if not files.exists('/var/run/supervisor.sock'):
        sudo('supervisord -c /etc/supervisor/supervisord.conf')
    supervisor.reload_config()


@task
def restart_services():
    command = 'redis-server /etc/redis.conf'
    require.files.directory('/var/log/redis', use_sudo=True, owner=env.user)
    require.files.file('/var/log/redis/error.log', owner=env.user, use_sudo=True)
    require.supervisor.process('redis', command=command,
            stdout_logfile='/var/log/redis/error.log')


@task
def install_machine():
    install_dependencies()
    add_users()
    install_services()
