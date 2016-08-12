#!/usr/bin/env python2
# -*- coding: utf-8 -*-
"""Script used to catch and expose e-mails from CFME"""

from __future__ import unicode_literals
from bottle import route, run, response, request
from collections import namedtuple
from datetime import datetime
from jinja2 import Environment, FileSystemLoader
from smtpd import SMTPServer
from utils.path import log_path, template_path
from utils.timeutil import parsetime
import asyncore
import email
import json
import re
import sqlite3
import sys
import threading


TIME_FORMAT = "%Y-%m-%d-%H-%M-%S"
ROWS = ("from_address", "to_address", "subject", "time", "text")

# Shared variable with all messages
db_lock = threading.RLock()
connection = sqlite3.connect(":memory:", check_same_thread=False)
cur = connection.cursor()
cur.execute(
    """
    CREATE TABLE emails (
        from_address TEXT,
        to_address TEXT,
        subject TEXT,
        time TIMESTAMP DEFAULT (datetime('now','localtime')),
        text TEXT
    )
    """
)
connection.commit()

# To write the e-mails into the files
files_lock = threading.RLock()  # To prevent filename collisions
test_name = None                # Name of the test which currently runs
email_path = log_path.join("emails")
email_folder = None             # Name of the root folder for testing

template_env = Environment(
    loader=FileSystemLoader(template_path.strpath)
)


def write(what, end="\n"):
    """Wrapper that forces flush on each write

    Args:
        what: What to print
        end: Ending character. Default LF
    """
    sys.stdout.write(what)
    if end is not None:
        sys.stdout.write(end)
    sys.stdout.flush()


class EmailServer(SMTPServer):
    """Simple e-mail server. What does it do is that every mail is put in the database."""
    def process_message(self, peer, mailfrom, rcpttos, data):
        message = email.message_from_string(data)
        payload = message.get_payload()
        if isinstance(payload, list):
            # Message can have multiple payloads, so let's join them for simplicity
            payload = "\n".join([x.get_payload().strip() for x in payload])
        d = dict(message.items())
        with db_lock:
            global connection
            cursor = connection.cursor()
            cursor.execute(
                "INSERT INTO emails VALUES (?, ?, ?, CURRENT_TIMESTAMP, ?)",
                (
                    d["From"],
                    ",".join([address.strip() for address in d["To"].strip().split(",")]),
                    d["Subject"],
                    payload)
            )
            connection.commit()
        if email_folder is not None:
            with files_lock:
                # Create directories if they don't exist
                current_test_folder = email_folder.join(test_name or "default-test")
                if not current_test_folder.exists():
                    current_test_folder.mkdir()
                arrived = datetime.now()

                def _getfname(counter):
                    return current_test_folder\
                        .join("%s-%d.eml" % (arrived.strftime("%Y%m%d%H%M%S"), int(counter)))
                cnt = 0
                while _getfname(cnt).exists():
                    cnt += 1
                with _getfname(cnt).open("w") as output:
                    # Dump the raw e-mail data
                    output.write(data)


@route("/set_test_name")
def set_test_name():
    """ Sets a test name for subsequent e-mails"""
    response.content_type = "application/json"
    if request.query.test_name:
        with files_lock:    # things under files_lock work with this one
            global test_name
            test_name = re.sub(r"[/?!]", ":", request.query.test_name)
            return json.dumps(True)
    else:
        return json.dumps(False)


@route("/messages")
def all_messages():
    """Return a JSON with all e-mails (eventually filtered)"""
    response.content_type = "application/json"

    # Build SQL
    sql = 'SELECT * FROM emails'

    # Build WHERE clause(s)
    bindings = ()
    where_clause = list()
    if request.query.from_address:
        where_clause.append("from_address = ?")
        bindings += (request.query.from_address,)
    if request.query.to_address:
        where_clause.append("to_address = ?")
        bindings += (request.query.to_address,)
    if request.query.subject:
        where_clause.append("subject = ?")
        bindings += (request.query.subject,)
    if request.query.subject_like:
        where_clause.append("subject LIKE ?")
        bindings += (request.query.subject_like,)
    if request.query.text_like:
        where_clause.append("text LIKE ?")
        bindings += (request.query.text_like,)
    if request.query.text:
        where_clause.append("text = ?")
        bindings += (request.query.text,)
    if request.query.time_from:
        time = parsetime.from_request_format(request.query.time_from)
        where_clause.append("time >= ?")
        bindings += (time,)
    if request.query.time_to:
        time = parsetime.from_request_format(request.query.time_to)
        where_clause.append("time <= ?")
        bindings += (time,)

    if where_clause:
        sql += ' WHERE {}'.format(" AND ".join(where_clause))

    # Order by time arrived
    sql += " ORDER BY time ASC"

    with db_lock:
        global connection
        db = connection.cursor()
        # execute query
        c = db.execute(sql, bindings)

        rows = c.fetchall()
        return json.dumps([dict(zip(ROWS, row)) for row in rows])


@route("/messages.html")
def all_messages_in_html():
    response.content_type = "text/html"
    emails = []
    Email = namedtuple("Email", ["source", "destination", "subject", "received", "body"])
    with db_lock:
        emails = map(Email._make, connection.cursor().execute("SELECT * FROM emails").fetchall())

    return template_env.get_template("smtp_result.html").render(emails=emails)


@route("/messages", method="DELETE")
def clear_database():
    """Clear the e-mail database"""
    response.content_type = "application/json"
    with db_lock:
        global connection
        cursor = connection.cursor()
        cursor.execute("DELETE FROM emails")
        connection.commit()
    return json.dumps(True)


def run_email_server(port=1025):
    EmailServer(("0.0.0.0", port), None)
    try:
        asyncore.loop()
    except KeyboardInterrupt:
        pass


def run_email_query(port=1026):
    try:
        run(host="0.0.0.0", port=port, quiet=True)
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    from argparse import ArgumentParser

    parser = ArgumentParser()
    parser.add_argument('--smtp-port', default=1025, type=int, help='port to bind the SMTP srv to')
    parser.add_argument('--query-port', default=1026, type=int, help='port for query interface')

    args = parser.parse_args()

    # Prepare the threads
    email_thread = threading.Thread(target=run_email_server, args=(args.smtp_port,))
    email_thread.daemon = True
    query_thread = threading.Thread(target=run_email_query, args=(args.query_port,))
    query_thread.daemon = True
    # Prepare folders
    if not email_path.exists():
        email_path.mkdir()
    seq_folder = 0
    while email_path.join(str(seq_folder)).exists():
        seq_folder += 1
    email_folder = email_path.join(str(seq_folder))
    if not email_folder.exists():
        email_folder.mkdir()
    # Create symlink
    latest_path_symlink = email_path.join("latest")
    if latest_path_symlink.exists():
        latest_path_symlink.remove()
    latest_path_symlink.mksymlinkto(email_folder)
    # RUN!
    email_thread.start()
    query_thread.start()
    write("Threads started ...")
    # Wait for finish
    try:
        while True:
            email_thread.join(2)
            query_thread.join(2)
    except KeyboardInterrupt:
        pass
    except:
        write("Exception raised!")
        raise
    finally:
        write("Finishing ...")
