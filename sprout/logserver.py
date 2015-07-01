#!/usr/bin/env python2
# -*- coding: utf-8 -*-
# Based on: https://docs.python.org/2.4/lib/network-logging.html
import atexit
try:
    import cPickle as pickle
except ImportError:
    import pickle
import logging
import logging.handlers
import SocketServer
import signal
import struct
from threading import Lock

from sprout import sprout_path
from utils.log import create_logger


logs_path = sprout_path.join("log")

logger_cache = {}

logger_cache_lock = Lock()

global_fs_lock = Lock()

MAX_FILE_SIZE = 20 * 1024 * 1024
MAX_BACKUPS = 10


def translate_sigterm_to_sigint(*args):
    raise KeyboardInterrupt


signal.signal(signal.SIGTERM, translate_sigterm_to_sigint)


@atexit.register
def close_logs():
    global logger_cache
    with logger_cache_lock:
        for filename, (logger, lock) in logger_cache.iteritems():
            with lock:
                for handler in logger.handlers:
                    if hasattr(handler, "close"):
                        try:
                            handler.close()
                        except Exception as e:
                            print "Could not close handler:", type(e).__name__, str(e)
        logger_cache = {}


class LogRecordStreamHandler(SocketServer.StreamRequestHandler):
    """Handler for a streaming logging request.

    This basically logs the record using whatever logging policy is
    configured locally.
    """

    def handle(self):
        """
        Handle multiple requests - each expected to be a 4-byte length,
        followed by the LogRecord in pickle format. Logs the record
        according to whatever policy is configured locally.
        """
        global logger_cache
        while True:
            chunk = self.connection.recv(4)
            if len(chunk) < 4:
                break
            slen = struct.unpack(">L", chunk)[0]
            chunk = self.connection.recv(slen)
            while len(chunk) < slen:
                chunk = chunk + self.connection.recv(slen - len(chunk))
            obj = pickle.loads(chunk)
            record = logging.makeLogRecord(obj)
            # if a name is specified, we use the named logger rather than the one
            # implied by the record.
            if self.server.logname is not None:
                name = self.server.logname
            else:
                name = record.name
            if not name:
                filename = logs_path.join("sprout.log")
            else:
                fields = name.split(".")
                fields[-1] += ".log"
                filename = logs_path
                for field in fields:
                    filename = filename.join(field)
                    if not field.endswith(".log"):
                        with global_fs_lock:
                            if not filename.exists():
                                filename.mkdir()
            filename = filename.strpath
            with logger_cache_lock:
                if filename in logger_cache:
                    logger, lock = logger_cache[filename]
                else:
                    logger = create_logger(
                        name, filename=filename, max_file_size=MAX_FILE_SIZE,
                        max_backups=MAX_BACKUPS)
                    lock = Lock()
                    logger_cache[filename] = (logger, lock)
            # N.B. EVERY record gets logged. This is because Logger.handle
            # is normally called AFTER logger-level filtering. If you want
            # to do filtering, do it at the client end to save wasting
            # cycles and network bandwidth!
            with lock:
                logger.handle(record)


class LogRecordSocketReceiver(SocketServer.ThreadingTCPServer):
    allow_reuse_address = 1

    def __init__(self, host='localhost',
                 port=logging.handlers.DEFAULT_TCP_LOGGING_PORT,
                 handler=LogRecordStreamHandler):
        SocketServer.ThreadingTCPServer.__init__(self, (host, port), handler)
        self.abort = 0
        self.timeout = 1
        self.logname = None

    def serve_until_stopped(self):
        import select
        abort = 0
        while not abort:
            rd, wr, ex = select.select([self.socket.fileno()],
                                       [], [],
                                       self.timeout)
            if rd:
                self.handle_request()
            abort = self.abort


def main():
    tcpserver = LogRecordSocketReceiver()
    print "About to start TCP server..."
    try:
        tcpserver.serve_until_stopped()
    except KeyboardInterrupt:
        print "Quitting"

if __name__ == "__main__":
    main()
