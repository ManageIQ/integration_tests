#!/usr/bin/env bash

[ -e ".env" ] && source .env

ACTION="${1}"
shift 1;
PIDFILE="./.sprout.pid"
LOGFILE="./sprout-manager.log"
UPDATE_LOG="./update.log"
FOREMAN_TIMEOUT=${FOREMAN_TIMEOUT:-300}  # Some tasks can take a long time so it is not good to interrupt them

hash foreman && {
    command="foreman start -t ${FOREMAN_TIMEOUT}"
} || {
    echo "You have to install ruby gem 'foreman' to manage Sprout"
    exit 2
}

function cddir() {
    BASENAME="`basename $0`"
    cd ${SPROUT_HOME:-$BASENAME}
}

function clearpyc() {
    echo "Clearing pyc cache"
    OLD=`pwd`
    cd ..
    find . -name \*.pyc -delete
    find . -name __pycache__ -delete
    cd "${OLD}"
}


function start_sprout() {
    cddir
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
    cddir
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
        echo "INT signal issued" >> $LOGFILE
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
    cddir
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
    cddir
    clearpyc
    echo "Running update"
    echo "--- Update begun at `date` ---" >> $UPDATE_LOG
    git checkout master >> $UPDATE_LOG && git pull origin master >> $UPDATE_LOG && {
        echo "Checking requirements"
        pip install -Ur requirements.txt >> $UPDATE_LOG
        echo "Migrating"
        ./manage.py migrate >> $UPDATE_LOG
        echo "Collecting static files"
        ./manage.py collectstatic --noinput >> $UPDATE_LOG
    }
    stop_sprout
    # Once more
    clearpyc
    start_sprout
    echo "--- Update finished at `date` ---" >> $UPDATE_LOG
}

case "${ACTION}" in
    start) start_sprout ;;
    stop) stop_sprout ;;
    restart) restart_sprout ;;
    update) update_sprout ;;
    running) running_sprout ;;
    *) echo "Usage: ${0} start|stop|restart|update|running" ;;
esac

