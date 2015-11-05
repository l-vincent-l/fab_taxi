from fabric.api import task, run, env, put
from fabric.context_managers import cd, shell_env
from fabtools import require, files, python
import requests, re, urllib, os
from sqlalchemy.engine import url
from sqlalchemy import create_engine

def table_exists(table_name, connection_string):
    return run('psql {} -tAc "SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = \'communes\');"'.format(connection_string)) == 't'

def create_drop_table_communes(connection_string):
    if table_exists('communes', connection_string):
        run('psql {} -c "drop table communes;"'.format(connection_string))
    run("""psql {} -c "
CREATE TABLE \"communes\" (gid serial,
\"commune\" varchar(100),
\"ref_insee\" varchar(5),
\"osm_id\" numeric,
\"population\" varchar(7),
\"code_posta\" varchar(250));
ALTER TABLE \"communes\" ADD PRIMARY KEY (gid);
SELECT AddGeometryColumn('','communes','geom','0','MULTIPOLYGON',2);
    " """.format(connection_string))

def get_departement_id(departement, connection_string):
    return run("psql {} -tAc \"SELECT id from departement where numero='{}'\"".\
        format(connection_string, departement))


def import_contours():
    base_url = 'http://export.openstreetmap.fr/contours-administratifs/communes/'
    r = requests.get(base_url)
    extension = '.shp.tar.gz'
    connection_string = env.conf_api.SQLALCHEMY_DATABASE_URI
    u = url.make_url(connection_string)
    create_drop_table_communes(connection_string)
    for f_name in re.findall(r'href=[\'"]?([^\'" >]+'+extension+')', r.content):
        run('wget {}{}'.format(base_url, f_name))
        f_name = urllib.unquote(f_name).decode('utf-8')
        departement = re.match('^([0-9]{2,3}|2A|2B)', f_name).group(0)
        basename = f_name[:-len(extension)]
        run(u'tar -xf {}'.format(f_name))
        run(u'shp2pgsql -a {0}.shp communes {1}  > {0}.sql'.format(basename,
            u.database))
        run(u'psql {} -f {}.sql'.format(env.conf_api.SQLALCHEMY_DATABASE_URI,
            basename))
        run('psql {} -c \'INSERT INTO \"ZUPC\" (nom, insee, shape, departement_id) (SELECT commune, ref_insee, geom, \'{}\' FROM communes);\''.format(connection_string,
            get_departement_id(departement, connection_string)))
        run('psql {} -c "truncate table communes;"'.format(connection_string))





@task
def import_zupc(import_='True'):
    require.files.directory('/tmp/zupc')
    with cd('/tmp/zupc/'):
        string = run("for i in *; do echo $i; done")
        files = string.replace("\r","").split("\n")
        for f in files:
            if f == '*':
                continue
            run('rm {}'.format(f))
        if import_=='True':
            import_contours()
        run('wget https://www.data.gouv.fr/s/resources/zones-uniques-de-prises-en-charge-des-taxis-zupc/20151023-174638/zupc.geojson')

    with python.virtualenv(env.relative_venv_path), cd(env.relative_api_path):
        with shell_env(APITAXI_CONFIG_FILE=env.config_filename):
            run('python manage.py load_zupc {} /tmp/zupc/zupc.geojson'.format(
                env.conf_api.SQLALCHEMY_DATABASE_URI))
