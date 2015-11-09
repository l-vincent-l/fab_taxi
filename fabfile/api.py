from fabric.contrib import files
from fabtools import require, git, python, nginx, supervisor, service
from fabric.context_managers import cd, shell_env
from fabric.api import put, run, task, env
from os import environ, path


def deploy_nginx_api_site():
    files.upload_template('templates/uwsgi.ini',  env.uwsgi_config_path,
        context={
           'config_path': env.apitaxi_config_path,
           'api_path': env.apitaxi_dir,
           'venv_path': env.apitaxi_venv_path,
           'uwsgi_socket': env.uwsgi_socket,
           'uwsgi_file': env.uwsgi_file,
           'uwsgi_pid_dir': env.wwwdata_piddir,
           'uwsgi_log_dir': env.wwwdata_logdir,
           'socket': env.uwsgi_socket,
           'processes': env.wsgi_processes,
           'threads': env.wsgi_threads
       }
    )

    uwsgi = path.join(env.apitaxi_venv_path, 'bin', 'uwsgi')
    require.supervisor.process('uwsgi',
        command='{} --ini {}'.format(uwsgi, env.uwsgi_config_path),
        directory=env.apitaxi_venv_path,
        stdout_logfile = '/var/log/nginx/apitaxi.log'
    )

    require.nginx.site('apitaxi',
        template_source='templates/nginx_site.conf',
        domain_name=getattr(env.conf_api, 'HOST', 'localhost'),
        port=getattr(env.conf_api, 'PORT', 80),
        socket=env.uwsgi_socket
    )


@task
def deploy_api():
    if files.exists(env.apitaxi_dir):
        return
    with cd(env.uwsgi_dir):
        git.clone('https://github.com/openmaraude/APITaxi')
        require.python.virtualenv(env.apitaxi_venv_path)
        with python.virtualenv(env.apitaxi_venv_path):
            python.install_pip()
            require.python.package('uwsgi')
        deploy_nginx_api_site()


@task
def upgrade_api():
    with python.virtualenv(env.apitaxi_venv_path), cd(env.apitaxi_dir):
        with shell_env(APITAXI_CONFIG_FILE=env.apitaxi_config_path):
            git.pull('.')
            put(environ['APITAXI_CONFIG_FILE'], env.apitaxi_config_path)
            python.install_requirements('requirements.txt')
            run('python manage.py db upgrade')
    restart_api()


@task
def restart_api():
    supervisor.restart_process('uwsgi')
    if service.is_running('nginx'):
        service.restart('nginx')
    else:
        service.start('nginx')
