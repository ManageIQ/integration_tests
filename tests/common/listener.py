#!/usr/bin/env python

# parse API get requests from CFME automate
# requires:
# * bottle, sqlite
# * port 8080 open
# example: curl -X PUT http://localhost:8080/events/VmRedhat/vm_name?event=vm_start

import os
import sys
import json
import sqlite3
from socket import gethostname
try:
    from bottle import run, route, request, response, install
except ImportError, e:
    print "Unable to import bottle.  Is python-bottle installed?"
    sys.exit(1)

try:
    from bottle_sqlite import SQLitePlugin
except ImportError, e:
    print "Unable to import bottle_sqlite.  Is python-bottle-sqlite installed?"
    sys.exit(1)

# If required, remove existing db
# FIXME, check perms too
db_file = "/tmp/eventdb.sqlite"
if os.path.isfile(db_file):
    os.unlink(db_file)

# Initialize database
conn = sqlite3.connect(db_file) # or use :memory: to put it in RAM
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
install(SQLitePlugin(dbfile=db_file))

if __name__ == '__main__':
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

        if where_clause:
            sql += ' WHERE %s' % " AND ".join(where_clause)

        # execute query
        c = db.execute(sql, bindings)

        rows = c.fetchall()
        return json.dumps([dict(r) for r in rows])

    @route('/events/<event_type>/<resource_name>', method='PUT')
    def event_put(db, event_type, resource_name):
        response.content_type = 'application/json'
        event = request.query.event
        c = db.executemany("INSERT INTO event_log VALUES (?, ?, ?, CURRENT_TIMESTAMP)", [(event_type, resource_name, event)])
        db.commit()
        return dict(result='success')

    @route('/events/<event_type>/<resource_name>', method='DELETE' )
    def event_delete(db, event_type, resource_name):
        # what if more than 2 rows match? rowid? timestamp?
        response.content_type = 'application/json'
        event = request.query.event
        c = db.execute("DELETE FROM event_log WHERE event_type = ? AND resource_name = ? AND event = ?", (event_type, resource_name, event))
        db.commit()
        return dict(result='success')

    run(host='0.0.0.0', port=8080, debug=True)
