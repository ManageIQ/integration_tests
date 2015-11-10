#!/usr/bin/env python2

# API listener to handle CFME automate events
# example calls
#    curl -X PUT http://localhost:8080/events/VmRedhat/vm_name?event=vm_start
#    curl -X GET http://localhost:8080/events

import json
import sqlite3
from datetime import datetime
from tempfile import NamedTemporaryFile

from bottle import run, route, request, response, install
from bottle_sqlite import SQLitePlugin

from utils.log import create_logger

db_file = NamedTemporaryFile()
logger = create_logger('events')

TIME_FORMAT = "%Y-%m-%d-%H-%M-%S"


def main(host, port, quiet):
    # Initialize database
    conn = sqlite3.connect(db_file.name)  # or use :memory: to put it in RAM
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE event_log (
        event_type TEXT,
        resource_name TEXT,
        event TEXT,
        event_time TIMESTAMP DEFAULT (datetime('now','localtime'))
    )
    """)

    # Install sqlite bottle plugin
    install(SQLitePlugin(dbfile=db_file.name))
    run(host=host, port=port, quiet=quiet)


def log_event(action, event_type=None, resource_name=None):
    if event_type and resource_name:
        logger.info('%s "%s" event for resource "%s"', action, event_type, resource_name)
    elif event_type:
        logger.info('%s "%s" event', action, event_type)


@route('/events', method='GET')
@route('/events/', method='GET')
@route('/events/<event_type>', method='GET')
@route('/events/<event_type>/<resource_name>', method='GET')
def events_list(db, event_type=None, resource_name=None):
    response.content_type = 'application/json'

    # Build SQL
    sql = 'SELECT * FROM event_log'

    # Build WHERE clause(s)
    bindings = ()
    where_clause = list()
    if event_type is not None:
        where_clause.append('event_type = ?')
        bindings += (event_type,)
    if resource_name is not None:
        where_clause.append('resource_name = ?')
        bindings += (resource_name,)
    if request.query.event:
        where_clause.append('event = ?')
        bindings += (request.query.event,)
    if request.query.time_from:
        time = datetime.strptime(request.query.time_from, TIME_FORMAT)
        where_clause.append("event_time >= ?")
        bindings += (time,)
    if request.query.time_to:
        time = datetime.strptime(request.query.time_to, TIME_FORMAT)
        where_clause.append("event_time <= ?")
        bindings += (time,)

    if where_clause:
        sql += ' WHERE %s' % " AND ".join(where_clause)

    # Order by time arrived
    sql += "  ORDER BY event_time ASC"

    # execute query
    c = db.execute(sql, bindings)

    rows = c.fetchall()
    return json.dumps([dict(r) for r in rows])


@route("/events_count", method="GET")
def events_count(db):
    response.content_type = "application/json"
    count = db.execute("SELECT COUNT(*) FROM event_log").fetchall()[0][0]
    return json.dumps({"count": count})


@route('/events/<event_type>/<resource_name>', method='PUT')
def event_put(db, event_type, resource_name):
    log_event('Adding', event_type, resource_name)
    response.content_type = 'application/json'
    event = request.query.event
    db.executemany("INSERT INTO event_log VALUES (?, ?, ?, CURRENT_TIMESTAMP)", [(event_type,
                                                                                  resource_name,
                                                                                  event)])
    db.commit()
    return dict(result='success')


@route('/events/<event_type>/<resource_name>', method='DELETE')
def event_delete(db, event_type, resource_name):
    log_event('Deleting', event_type, resource_name)
    # what if more than 2 rows match? rowid? timestamp?
    response.content_type = 'application/json'
    event = request.query.event
    db.execute("DELETE FROM event_log WHERE event_type = ? AND resource_name = ? AND event = ?",
               (event_type, resource_name, event))
    db.commit()
    return dict(result='success')


@route('/events', method='DELETE')
def clear_database(db):
    logger.info('Deleting all events')
    response.content_type = 'application/json'
    db.execute("DELETE FROM event_log")
    db.commit()
    return dict(result="success")

if __name__ == '__main__':
    from argparse import ArgumentParser

    parser = ArgumentParser()
    parser.add_argument('host', default='0.0.0.0', nargs='?',
        help='address to bind to')
    parser.add_argument('port', default=65432, type=int, nargs='?',
        help='port to bind to')
    parser.add_argument('--quiet', '-q', default=False, action='store_true',
        help='suppress bottle output')

    args = parser.parse_args()

    main(host=args.host, port=args.port, quiet=args.quiet)
