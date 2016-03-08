Pre-requisites
==============

You need to have a clean debian8 system
A root user with ssh access

We recommend to use a virtual env, and install the requirements with:
`pip install -r requirements.txt`

Configuration
=============

Open fabfile/env.py copy/paste the load_config_dev function (with the decorator)
, change its name and edit values to suit your needs.
Now you need to import it in fabfile/__init__.py.
Open it, you'll find a line that looks like:
`from env import env, load_config_dev` add at the end of the line :
`, name_of_your_function`.

You also need a APITaxi configuration file.

Install system
==============

The first step is to install the system, it will create a linux user deploy,
install and update packages.

Run: `APITAXI_CONFIG_FILE=api_settings.py fab load_config_function install_sytem`

Deploy
=====

To deploy a new version you can run : `APITAXI_CONFIG_FILE=api_settings.py fab load_config_function deploy`
