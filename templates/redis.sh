#!/usr/bin/env bash
APITAXI_CONFIG_FILE=%(deployment_dir)s/APITaxi-master/APITaxi/prod_settings.py %(deployment_dir)s/venvAPITaxi/bin/python %(deployment_dir)s/APITaxi-master/manage.py warm_up_redis &
redis-server /etc/redis.conf

