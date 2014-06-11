#!/usr/bin/env bash

PIDFILE="/tmp/snmp_listen.pid"

# Source the EVM env.
. /etc/default/evm

function log()
{
    echo "${0}: ${@}"
}

function stop()
{
    [ -e "${PIDFILE}" ] && {
        PID=`cat "${PIDFILE}"`
        kill -s INT $PID > /dev/null 2>&1
        [ $? -ne 0 ] && {
            log "Could not kill the listener with pid ${PID}, is it already stopped?" 
        }
        rm -f "${PIDFILE}"
    } || {
        log "No pid file present, the listener is probably not running."
    }
}

function start()
{
    [ -e "${PIDFILE}" ] && stop
    ruby snmp_listen.rb >/dev/null 2>&1 &
    PID=$!
    echo "${PID}" > "${PIDFILE}"
    echo "Listener running with pid ${PID}"
}

[ $# -ne 1 ] && {
    echo "You must specify action, start|stop"
    exit 1
}

[ "${1}" == "start" ] && {
    start
} || {
    [ "${1}" == "stop" ] && {
        stop
    } || {
        log "Unknown command ${1}"
        exit 2
    }
}
