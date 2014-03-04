#!/usr/bin/env python

# API listener to handle CFME automate events
# example calls
#    curl -X PUT http://localhost:8080/events/VmRedhat/vm_name?event=vm_start
#    curl -X GET http://localhost:8080/events

import os
import json
import sqlite3
import sys
import tempfile
from bottle import run, route, request, response, install
from bottle_sqlite import SQLitePlugin
from datetime import datetime

# If required, remove existing db
# FIXME, check perms too
fd, db_file = tempfile.mkstemp()
f = os.fdopen(fd)   # It's needed to close the file
f.close()

# Initialize database
conn = sqlite3.connect(db_file)  # or use :memory: to put it in RAM
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


TIME_FORMAT = "%Y-%m-%d-%H-%M-%S"

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
        response.content_type = 'application/json'
        event = request.query.event
        db.executemany("INSERT INTO event_log VALUES (?, ?, ?, CURRENT_TIMESTAMP)", [(event_type,
                                                                                      resource_name,
                                                                                      event)])
        db.commit()
        return dict(result='success')

    @route('/events/<event_type>/<resource_name>', method='DELETE')
    def event_delete(db, event_type, resource_name):
        # what if more than 2 rows match? rowid? timestamp?
        response.content_type = 'application/json'
        event = request.query.event
        db.execute("DELETE FROM event_log WHERE event_type = ? AND resource_name = ? AND event = ?",
                   (event_type, resource_name, event))
        db.commit()
        return dict(result='success')

    @route('/events', method='DELETE')
    def clear_database(db):
        response.content_type = 'application/json'
        db.execute("DELETE FROM event_log")
        db.commit()
        return dict(result="success")

    port = 65432
    if len(sys.argv) == 2:
        port = int(sys.argv[-1])
    run(host='0.0.0.0', port=port)
