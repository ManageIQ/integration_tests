from bottle import request, route, run, template
import os
import subprocess
import tempfile
import sys
import cgi
import signal

try:
    with open(sys.argv[2], "r") as f:
        allowed_files = f.readlines()
except IOError:
    print "allowed.files not found, exiting"
    sys.exit(127)
allowed_files = [path.strip("\n") for path in allowed_files]

template_dir = os.path.dirname(__file__)


class Log(object):
    def __init__(self, fname):
        self.fname = fname
        self.running = False
        self.start(first_run=True)

    def start(self, first_run=False):
        if not first_run:
            self.f.close()
        self.f = tempfile.NamedTemporaryFile()
        self.proc = subprocess.Popen(['/usr/bin/tail', '-f', self.fname], stdout=self.f)
        self.running = True

    def stop(self):
        self.proc.kill()
        self.running = False

    def delete(self):
        self.stop()
        self.f.close()

    def reset(self):
        self.stop()
        self.start()

    def get(self):
        with open(self.f.name, "rb") as infile:
            return infile.read()

    def size(self):
        if self.running:
            return os.path.getsize(self.f.name)

Loggers = {}


def die(a, b):
    for logger in Loggers:
        Loggers[logger].stop()
    sys.exit()

signal.signal(signal.SIGTERM, die)


@route('/setup/<path:path>')
def setup(path):
    path = os.path.abspath("/" + path)
    if any([path.startswith(allowed) for allowed in allowed_files]):
        base, tail = os.path.split(path)
        Loggers[tail] = Log(path)


def get_data():
    data = []
    for name, logger in Loggers.iteritems():
        data.append({'name': name,
                'tmp_name': logger.f.name,
                'size': logger.size(),
                'filename': logger.fname,
                'running': logger.running})
    return data


@route('/gui/', method=["get", "post"])
def lister():
    op = request.forms.get('op', None)
    name = request.forms.get('name', None)
    if op == "start":
        Loggers[name].start()
    elif op == "stop":
        Loggers[name].stop()
    elif op == "delete":
        Loggers[name].delete()
        del Loggers[name]
    elif op == "reset":
        Loggers[name].reset()
    elif op == "view":
        file_data = cgi.escape(Loggers[name].get())
        return template("merkyl", logs=[], file_data=file_data, template_lookup=[template_dir])
    elif op == "raw":
        return Loggers[name].get()
    elif op == "add":
        path = request.forms.get('filename', None)
        if path:
            path = os.path.abspath(path)
            if any([path.startswith(allowed) for allowed in allowed_files]):
                base, tail = os.path.split(path)
                Loggers[tail] = Log(path)
    elif op == "quit":
        for logger in Loggers:
            Loggers[logger].delete()
        Loggers.clear()
        sys.stderr.close()
    elif op == "deleteall":
        for logger in Loggers:
            Loggers[logger].delete()
        Loggers.clear()
    elif op == "resetall":
        for logger in Loggers:
            Loggers[logger].reset()
    elif op == "stopall":
        for logger in Loggers:
            Loggers[logger].stop()

    return template("merkyl", logs=get_data(), file_data=False, template_lookup=[template_dir])


@route('/get/<name>')
def get(name):
    return Loggers[name].get()


@route('/reset/<name>')
def reset(name):
    Loggers[name].reset()


@route('/stop/<name>')
def stop(name):
    Loggers[name].stop()


@route('/start/<name>')
def start(name):
    Loggers[name].start()


@route('/delete/<name>')
def delete(name):
    Loggers[name].delete()
    del Loggers[name]


@route('/deleteall')
def deleteall():
    for logger in Loggers:
        Loggers[logger].delete()
    Loggers.clear()


@route('/resetall')
def resetall():
    for logger in Loggers:
        Loggers[logger].reset()


@route('/quit')
def quit():
    for logger in Loggers:
        Loggers[logger].delete()
        del Loggers[logger]
    sys.stderr.close()


def main():
    run(host='0.0.0.0', port=sys.argv[1])


if __name__ == "__main__":
    main()
