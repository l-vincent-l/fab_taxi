#coding: utf-8
from fabric.api import run, env

def wget(url):
    return run(u'wget {}'.format(url))

def list_dir():
    string_ = run("for i in %s/*; do echo $i; done" % env.cwd)
    files = string_.replace("\r","").split("\n")
    return files
