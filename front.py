#/usr/bin/python
# -*- coding: utf-8 -*-
from gevent import monkey
monkey.patch_all()
import gevent

from flask import Flask
from flask.ext.pymongo import PyMongo
from flask import current_app

import uwsgi
from uwsgidecorators import spoolraw

api = Flask(__name__)

api.config['MONGO_HOST'] = 'localhost'
api.config['MONGO_DBNAME'] = 'test'
api.mongo = PyMongo(api)

api.last_count = 0


def increment_counter():
    try:
        with api.app_context():
            current_app.mongo.db.counter.update(
                {'_id': 'counter'},
                {'$inc': {'value': 1}}
            )
    except Exception:
        if uwsgi.i_am_the_spooler():
            raise
        else:
            spooler.spool({'message': '1'})


def get_counter():
    try:
        with api.app_context():
            doc = current_app.mongo.db.counter.find_one({'_id': 'counter'})
            current_count = int(doc['value'])
            current_app.last_count = current_count
    except Exception:
        return None
    else:
        return current_count


@api.route('/')
def show_counter():
    # get the current counter from mongoDB in a concurrent way
    g = gevent.spawn(get_counter)
    g.join()
    counter = g.value or api.last_count
    counter = "{:,}".format(counter)

    # increment the application wide counter
    gevent.spawn(increment_counter)

    return """<h1>%sé</h1>
<script>
function refresh() {
    window.location.reload(true);
    setTimeout(refresh, 10000);
</script>
""" % str(counter)


# Spooling interval
uwsgi.set_spooler_frequency(15)


@spoolraw
def spooler(env):
    try:
        increment_counter()
    except Exception as e:
        print str(e)
        return uwsgi.SPOOL_RETRY
    else:
        return uwsgi.SPOOL_OK
