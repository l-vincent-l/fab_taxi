#coding: utf-8
from fabtools import require, git, python, nginx, supervisor, service, files
from fabric.context_managers import cd, shell_env
from fabric.api import put, run, task, env
from os import environ, path
import time, re
from .dash import restart_stats_workers

@task
def test_uwsgi_is_started(now):
    for i in range(1, 30):
        status = supervisor.process_status('uwsgi_{}'.format(now))
        if status == 'RUNNING':
            break
        time.sleep(1)
    testing_file = '/tmp/test_uwsgi.py'
    if files.is_file(testing_file):
        files.remove(testing_file)
    put('files/test_uwsgi.py', '/tmp/')

    require.python.package('six', use_sudo=True)
    output = run('python {} {} {} aa'.format(testing_file, env.uwsgi_socket_api(now),
        '{}/ads/'.format(env.conf_api.SERVER_NAME)))
    assert '"message"' in output

    from test_api import test_api
    test_api(testing_file, env.uwsgi_socket_api(now), env.conf_api.SERVER_NAME)


def install_swagger_ui():
    with cd('~'):
        if not files.exists('APITaxi_swagger'):
            git.clone('https://github.com/openmaraude/APITaxi_swagger')
        git.checkout('APITaxi_swagger')
        git.pull('APITaxi_swagger')
        return path.join(run('pwd'), 'APITaxi_swagger')

def install_zupc_cache():
    with cd('~'):
        p = path.join(run('pwd'), 'zupc', 'zupc')
        require.files.directory(p)
        require.files.file(path.join(p, "index.html"), source="files/zupc.html")
        return p


def deploy_nginx_api_site(now):
    files.upload_template('templates/uwsgi.ini',  env.uwsgi_api_config_path(now),
        context={
           'config_path': env.apitaxi_config_path(now),
           'api_path': env.apitaxi_dir(now),
           'venv_path': env.apitaxi_venv_path(now),
           'uwsgi_file': env.uwsgi_api_file(now),
           'uwsgi_pid_file': env.uwsgi_api_pid_file(now),
           'uwsgi_log_file1': env.uwsgi_logdir + '/api_launcher.log',
           'uwsgi_log_file2': env.uwsgi_logdir + '/api_uwsgi.log',
           'uwsgi_launcher_logdir': env.uwsgi_launcher_logdir,
           'socket': env.uwsgi_socket_api(now),
           'processes': env.wsgi_processes,
           'threads': env.wsgi_threads,
           'now': now
       }
    )

    files.upload_template('templates/uwsgi.ini',  env.uwsgi_front_config_path(now),
        context={
           'config_path': env.fronttaxi_config_path(now),
           'api_path': env.fronttaxi_dir(now),
           'venv_path': env.apitaxi_venv_path(now),
           'uwsgi_file': env.uwsgi_front_file(now),
           'uwsgi_pid_file': env.uwsgi_front_pid_file(now),
           'uwsgi_log_file1': env.uwsgi_logdir + '/front_launcher.log',
           'uwsgi_log_file2': env.uwsgi_logdir + '/front_uwsgi.log',
           'socket': env.uwsgi_socket_front(now),
           'processes': env.wsgi_processes,
           'threads': env.wsgi_threads,
           'now': now
       }
    )

    uwsgi = path.join(env.apitaxi_venv_path(now), 'bin', 'uwsgi')
    require.supervisor.process('uwsgi_api_{}'.format(now),
        command='{} --ini {}'.format(uwsgi, env.uwsgi_api_config_path(now)),
        directory=env.apitaxi_venv_path(now),
        stdout_logfile = '/var/log/nginx/apitaxi.log',
        user='www-data'
    )

    require.supervisor.process('uwsgi_front_{}'.format(now),
        command='{} --ini {}'.format(uwsgi, env.uwsgi_front_config_path(now)),
        directory=env.apitaxi_venv_path(now),
        stdout_logfile = '/var/log/nginx/fronttaxi.log',
        user='www-data'
    )

    test_uwsgi_is_started(now)

    celery = path.join(env.apitaxi_venv_path(now), 'bin', 'celery')
    worker_name = 'send_hail_{}'.format(now)
    command = '{} worker --app=celery_worker.celery -Q {} -n {} --workdir={}'
    require.supervisor.process(worker_name,
        command=command.format(celery, worker_name, worker_name, env.apitaxi_dir(now)),
        directory=env.apitaxi_dir(now),
        stdout_logfile='/var/log/celery/send_hail.log',
        user='www-data',
        environment='APITAXI_CONFIG_FILE=prod_settings.py'
    )

    swagger_dir = install_swagger_ui()
    zupc_dir = install_zupc_cache()

    require.nginx.site('apitaxi',
        template_source='templates/nginx_site.conf',
        domain_name=getattr(env.conf_api, 'HOST', 'localhost'),
        env='NOW={}'.format(now),
        port=getattr(env.conf_api, 'PORT', 80),
        socket_api=env.uwsgi_socket_api(now),
        socket_front=env.uwsgi_socket_front(now),
        doc_dir=swagger_dir,
        zupc_cache_dir=zupc_dir
    )

    path_redis = '{}/redis.sh'.format(env.deployment_dir(now))
    require.files.template_file(path=path_redis,
                               template_source='templates/redis.sh',
                               context={'deployment_dir':env.deployment_dir(now)},
                               mode='770')
    require.supervisor.process('redis',
            command=path_redis,
            stdout_logfile='/var/log/redis/error.log'
    )


def clean_directories(now):
    l = run('for i in {}/deployment_*; do echo $i; done'.format(env.deploy_dir)).split("\n")
    for d in [d.replace('\r', '') for d in l]:
        if not files.is_dir(d):
            continue
        if d == env.deployment_dir(now):
            continue
        files.remove(d, recursive=True)

    l = run('for i in {}/apitaxi_*; do echo $i; done'.format(env.uwsgi_socket_dir)).split("\n")
    for f in [f.replace('\r', '') for f in l]:
        if f == env.uwsgi_socket_api(now):
            continue
        files.remove(f, use_sudo=True)
    #The pid file should be remove when the process stops

def stop_old_processes(now):
    def stop_process(name, visitor):
        l = run('for i in /etc/supervisor/conf.d/{}_*; do echo $i; done'.format(name)).split("\n")
        for f in [f.replace('\r', '') for f in l]:
            print 'To remove: {}'.format(f)
            if str(now) in f:
                continue
            file_ = f.split('/')[-1]
            process = file_[:-len('.conf')]
            visitor(process)
            files.remove(f, use_sudo=True)

    stop_process('uwsgi', lambda p:supervisor.stop_process(p))
    def stop_queues(process):
        #Request' status is failure after 15 secs in received
        #So even if queue is not empty we can shutdown the process
        for i in range(1, 17):
            res = run('python manage.py active_tasks {}'.format(process))
            if res == '':
                break
            time.sleep(1)
        supervisor.stop_process(process)

    with cd(env.apitaxi_dir(now)):
        with python.virtualenv(env.apitaxi_venv_path(now)),\
             shell_env(APITAXI_CONFIG_FILE=env.apitaxi_config_path(now)):
            stop_process('send_hail', stop_queues)


def deploy_front(now):
    with cd(env.deployment_dir(now)):
        run(u'wget {} -O front.zip'.format(env.fronttaxi_archive))
        run('unzip front.zip')
    with cd(env.fronttaxi_dir(now)), python.virtualenv(env.apitaxi_venv_path(now)):
        python.install_requirements('requirements.txt')
        put(environ['APITAXI_CONFIG_FILE'], env.fronttaxi_config_path(now))


def get_admin_key():
    return run(
            """psql {} -tAc 'SELECT apikey FROM "user" where email='"'"'admin'"'"';'"""\
                    .format(env.conf_api.SQLALCHEMY_DATABASE_URI))


def install_admin_user():
    if len(get_admin_key()) > 0:
        return
    run('python manage.py create_admin admin')


@task
def deploy_api(commit='master'):
    now = int(time.time())
    require.files.directory(env.deployment_dir(now))
    with cd(env.deployment_dir(now)):
        run(u'wget {}'.format(env.apitaxi_archive.format(commit)))
        run('unzip {}.zip'.format(commit))
        if commit != 'master':
            run('mv APITaxi-{} APITaxi-master'.format(commit))

    with cd(env.apitaxi_dir(now)):
        require.python.virtualenv(env.apitaxi_venv_path(now))
        with python.virtualenv(env.apitaxi_venv_path(now)):
            python.install_pip(use_sudo=False)
            require.python.package('uwsgi')
            python.install_requirements('requirements.txt')
            put(environ['APITAXI_CONFIG_FILE'], env.apitaxi_config_path(now))
            with shell_env(APITAXI_CONFIG_FILE=env.apitaxi_config_path(now)):
                for i in range(1, 30):
                    if service.is_running('supervisor'):
                        break
                    time.sleep(1)
                run('python manage.py db upgrade')
                install_admin_user()
        deploy_front(now)
        deploy_nginx_api_site(now)
    if not service.is_running('nginx'):
        service.start('nginx')
    clean_directories(now)
    stop_old_processes(now)
    restart_stats_workers(now)
