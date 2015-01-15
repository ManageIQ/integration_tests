#!/usr/bin/env bash

[ -e ".env" ] && source .env

ACTION="${1}"
shift 1;
PIDFILE="./.sprout.pid"
LOGFILE="./sprout-manager.log"
UPDATE_LOG="./update.log"

hash foreman && {
    command="foreman start -t 180"
    flush_redis=false
} || {
    command="honcho start"
    flush_redis=true
}


function start_sprout() {
    if [ -e "${PIDFILE}" ] ;
    then
        ps -p `cat $PIDFILE` >/dev/null
        if [ $? -eq 0 ] ;
        then
            echo "Sprout is already running!"
            return 1
        fi
        rm -f $PIDFILE
    fi
    echo "Starting Sprout"
    echo "--- Log opened at `date` ---" >> $LOGFILE
    $command > $LOGFILE 2>&1 &
    PID=$!
    echo $PID > $PIDFILE
    echo "Sprout is running!"
}

function stop_sprout() {
    if [ -e "${PIDFILE}" ] ;
    then
        PID=`cat $PIDFILE`
        ps -p $PID >/dev/null
        if [ $? -ne 0 ] ;
        then
            echo "Sprout is already stopped!"
            rm -f $PIDFILE
            return 1
        fi
        kill -INT $PID
        echo "Waiting for the Sprout to stop"
        while kill -0 "$PID" >/dev/null 2>&1 ; do
            sleep 0.5
        done
        rm -f $PIDFILE
        echo "--- Log closed at `date` ---" >> $LOGFILE
        return 0
    else
        echo "No pidfile present, Sprout probably not running"
        return 1
    fi
}

function running_sprout() {
    if [ -e "${PIDFILE}" ] ;
    then
        ps -p `cat $PIDFILE` >/dev/null
        if [ $? -eq 0 ] ;
        then
            echo "running"
            return 0
        else:
            echo "not running"
            return 1
        fi
    else
        echo "not running"
        return 1
    fi
}

function restart_sprout() {
    stop_sprout
    start_sprout
}

function update_sprout() {
    echo "Running update"
    git checkout master > $UPDATE_LOG && git pull origin master > $UPDATE_LOG && {
        echo "Checking requirements"
        pip install -Ur requirements.txt > $UPDATE_LOG
        echo "Migrating"
        ./manage.py migrate > $UPDATE_LOG
        echo "Collecting static files"
        ./manage.py collectstatic --noinput > $UPDATE_LOG
    }
    stop_sprout
    echo "Clearing pyc cache"
    OLD=`pwd`
    cd ..
    find . -name \*.pyc -delete
    find . -name __pycache__ -delete
    cd "${OLD}"
    if $flush_redis ;
    then
        echo "Flushing redis"
        redis-cli -p ${REDIS_PORT:-6379} FLUSHDB
        redis-cli -p ${REDIS_PORT:-6379} FLUSHALL
    fi
    start_sprout
}

case "${ACTION}" in
    start) start_sprout ;;
    stop) stop_sprout ;;
    restart) restart_sprout ;;
    update) update_sprout ;;
    running) running_sprout ;;
    *) echo "Usage: ${0} start|stop|restart|update|running" ;;
esac

