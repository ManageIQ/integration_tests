#!/usr/bin/env bash

hash memcached 2>/dev/null || {
    echo "Please install memcached"
    exit 3
}

hash gunicorn 2>/dev/null && hash celery 2>/dev/null || {
    echo "Please run pip install -Ur requirements.txt"
    exit 3
}

[ -e ".env" ] && source .env

YAMLS_DIR=${YAMLS_DIR:-"../../cfme-qe-yamls"}
BACKUP_DIR=${BACKUP_DIR:-"/tmp/sprout-backup"}

PYTHONPATH="`pwd`:${PYTHONPATH}"
export PYTHONPATH

ACTION="${1}"
shift 1;
PIDFILE_GUNICORN="./.sprout.gunicorn.pid"
PIDFILE_MEMCACHED="./.sprout.memcached.pid"
PIDFILE_WORKER="./.sprout.worker.pid"
PIDFILE_BEAT="./.sprout.beat.pid"
PIDFILE_FLOWER="./.sprout.flower.pid"
PIDFILE_LOGSERVER="./.sprout.logserver.pid"
LOGFILE="./sprout-manager.log"
UPDATE_LOG="./update.log"
GUNICORN_CMD="gunicorn --bind 127.0.0.1:${DJANGO_PORT:-8000} -w ${GUNICORN_WORKERS:-4} --access-logfile access.log --error-logfile error.log sprout.wsgi:application"
MEMCACHED_CMD="memcached -l 127.0.0.1 -p ${MEMCACHED_PORT:-23156}"
WORKER_CMD="./celery_runner worker --app=sprout.celery:app --concurrency=${CELERY_MAX_WORKERS:-8} --loglevel=INFO -Ofair"
BEAT_CMD="./celery_runner beat --app=sprout.celery:app"
FLOWER_CMD="./celery_runner flower --app=sprout.celery:app"
LOGSERVER_CMD="./logserver.py"

true
TRUE=$?
false
FALSE=$?

function cddir() {
    BASENAME="`dirname $0`"
    cd ${SPROUT_HOME:-$BASENAME} || exit
}

function needs_update() {
    cddir
    OLD=`pwd`
    cd ..
    git fetch origin >/dev/null 2>&1
    git diff --name-only `git rev-parse master` `git rev-parse origin/master` | grep -E "^sprout|^utils/mgmt_system|^utils/appliance"
    RESULT=$?
    cd "${OLD}" || exit
    return $RESULT
}

function update_yamls() {
    cddir
    pushd $YAMLS_DIR
    git pull origin master >/dev/null 2>&1
    RESULT=$?
    [ $RESULT -ne 0 ] && echo "Pull on yamls git repo failed"
    popd
    return $RESULT
}

function clearpyc() {
    echo ">> Clearing pyc cache"
    OLD=`pwd`
    cd ..
    find . -name \*.pyc -delete
    find . -name __pycache__ -delete
    cd "${OLD}" || exit
}

function migrations_needed() {
    cddir
    ./manage.py migrate -l | fgrep "[ ]" >/dev/null
    RESULT=$?
    if [ $RESULT -eq 0 ] ;
    then
        return $TRUE
    else
        return $FALSE
    fi
}

##
#
# MEMCACHED functions
#
function start_memcached() {
    cddir
    if [ -e "${PIDFILE_MEMCACHED}" ] ;
    then
        ps -p "$(cat "$PIDFILE_MEMCACHED")" >/dev/null
        if [ $? -eq 0 ] ;
        then
            echo ">> Memcached is already running!"
            return 1
        fi
        rm -f $PIDFILE_MEMCACHED
    fi

    echo ">> Starting Memcached"
    $MEMCACHED_CMD > $LOGFILE 2>&1 &
    PID=$!
    echo $PID > $PIDFILE_MEMCACHED
    echo ">> Memcached is running!"
}

function stop_memcached() {
    cddir
    if [ -e "${PIDFILE_MEMCACHED}" ] ;
    then
        PID=`cat $PIDFILE_MEMCACHED`
        ps -p $PID >/dev/null
        if [ $? -ne 0 ] ;
        then
            echo ">> Memcached is already stopped!"
            rm -f $PIDFILE_MEMCACHED
            return 1
        fi
        kill -INT $PID
        echo "INT signal issued to Memcached" >> $LOGFILE
        echo ">> Waiting for the Memcached to stop"
        while kill -0 "$PID" >/dev/null 2>&1 ; do
            sleep 0.5
        done
        rm -f $PIDFILE_MEMCACHED
        return 0
    else
        echo ">> No pidfile present, Memcached probably not running"
        return 1
    fi
}


##
#
# LOGSERVER functions
#
function start_logserver() {
    cddir
    if [ -e "${PIDFILE_LOGSERVER}" ] ;
    then
        ps -p "$(cat "$PIDFILE_LOGSERVER")" >/dev/null
        if [ $? -eq 0 ] ;
        then
            echo ">> Logserver is already running!"
            return 1
        fi
        rm -f $PIDFILE_LOGSERVER
    fi

    echo ">> Starting Logserver"
    $LOGSERVER_CMD > $LOGFILE 2>&1 &
    PID=$!
    echo $PID > $PIDFILE_LOGSERVER
    echo ">> Logserver is running!"
}

function stop_logserver() {
    cddir
    if [ -e "${PIDFILE_LOGSERVER}" ] ;
    then
        PID=`cat $PIDFILE_LOGSERVER`
        ps -p $PID >/dev/null
        if [ $? -ne 0 ] ;
        then
            echo ">> Logserver is already stopped!"
            rm -f $PIDFILE_LOGSERVER
            return 1
        fi
        kill -TERM $PID
        echo "TERM signal issued to Logserver" >> $LOGFILE
        echo ">> Waiting for the Logserver to stop"
        while kill -0 "$PID" >/dev/null 2>&1 ; do
            sleep 0.5
        done
        rm -f $PIDFILE_LOGSERVER
        return 0
    else
        echo ">> No pidfile present, Logserver probably not running"
        return 1
    fi
}


###
#
# GUNICORN functions
#
function start_gunicorn() {
    cddir
    if [ -e "${PIDFILE_GUNICORN}" ] ;
    then
        ps -p "$(cat "$PIDFILE_GUNICORN")" >/dev/null
        if [ $? -eq 0 ] ;
        then
            echo ">> Gunicorn is already running!"
            return 1
        fi
        rm -f $PIDFILE_GUNICORN
    fi

    echo ">> Starting Gunicorn"
    $GUNICORN_CMD > $LOGFILE 2>&1 &
    PID=$!
    echo $PID > $PIDFILE_GUNICORN
    echo ">> Gunicorn is running!"
}

function stop_gunicorn() {
    cddir
    if [ -e "${PIDFILE_GUNICORN}" ] ;
    then
        PID=`cat $PIDFILE_GUNICORN`
        ps -p $PID >/dev/null
        if [ $? -ne 0 ] ;
        then
            echo ">> Gunicorn is already stopped!"
            rm -f $PIDFILE_GUNICORN
            return 1
        fi
        kill -INT $PID
        echo "INT signal issued to Gunicorn" >> $LOGFILE
        echo ">> Waiting for the Gunicorn to stop"
        while kill -0 "$PID" >/dev/null 2>&1 ; do
            sleep 0.5
        done
        rm -f $PIDFILE_GUNICORN
        return 0
    else
        echo ">> No pidfile present, Gunicorn probably not running"
        return 1
    fi
}

function reload_gunicorn() {
    cddir
    if [ -e "${PIDFILE_GUNICORN}" ] ;
    then
        PID=`cat $PIDFILE_GUNICORN`
        ps -p $PID >/dev/null
        if [ $? -ne 0 ] ;
        then
            echo ">> Gunicorn is already stopped!"
            start_gunicorn
        else
            kill -HUP $PID
            echo ">> Gunicorn reloaded"
        fi
        return 0
    else
        echo ">> No pidfile present, Gunicorn probably not running"
        return 1
    fi
}

###
#
# CELERY worker functions
#
function start_worker() {
    cddir
    if [ -e "${PIDFILE_WORKER}" ] ;
    then
        ps -p "$(cat "$PIDFILE_WORKER")" >/dev/null
        if [ $? -eq 0 ] ;
        then
            echo ">> Worker is already running!"
            return 1
        fi
        rm -f $PIDFILE_WORKER
    fi

    echo ">> Starting Worker"
    $WORKER_CMD > $LOGFILE 2>&1 &
    PID=$!
    echo $PID > $PIDFILE_WORKER
    echo ">> Worker is running!"
}

function stop_worker() {
    cddir
    if [ -e "${PIDFILE_WORKER}" ] ;
    then
        PID=`cat $PIDFILE_WORKER`
        ps -p $PID >/dev/null
        if [ $? -ne 0 ] ;
        then
            echo ">> Worker is already stopped!"
            rm -f $PIDFILE_WORKER
            return 1
        fi
        kill -TERM $PID
        echo "TERM signal issued to Worker" >> $LOGFILE
        echo ">> Waiting for the Worker to stop"
        while kill -0 "$PID" >/dev/null 2>&1 ; do
            sleep 0.5
        done
        rm -f $PIDFILE_WORKER
        return 0
    else
        echo ">> No pidfile present, Worker probably not running"
        return 1
    fi
}

###
#
# CELERY beat functions
#
function start_beat() {
    cddir
    if [ -e "${PIDFILE_BEAT}" ] ;
    then
        ps -p "$(cat "$PIDFILE_BEAT")" >/dev/null
        if [ $? -eq 0 ] ;
        then
            echo ">> Beat is already running!"
            return 1
        fi
        rm -f $PIDFILE_BEAT
    fi

    echo ">> Starting Beat"
    $BEAT_CMD > $LOGFILE 2>&1 &
    PID=$!
    echo $PID > $PIDFILE_BEAT
    echo ">> Beat is running!"
}

function stop_beat() {
    cddir
    if [ -e "${PIDFILE_BEAT}" ] ;
    then
        PID=`cat $PIDFILE_BEAT`
        ps -p $PID >/dev/null
        if [ $? -ne 0 ] ;
        then
            echo ">> Beat is already stopped!"
            rm -f $PIDFILE_BEAT
            return 1
        fi
        kill -TERM $PID
        echo "TERM signal issued to Beat" >> $LOGFILE
        echo ">> Waiting for the Beat to stop"
        while kill -0 "$PID" >/dev/null 2>&1 ; do
            sleep 0.5
        done
        rm -f $PIDFILE_BEAT
        return 0
    else
        echo ">> No pidfile present, Beat probably not running"
        return 1
    fi
}


###
#
# CELERY flower functions
#
function start_flower() {
    cddir
    if [ -e "${PIDFILE_FLOWER}" ] ;
    then
        ps -p "$(cat "$PIDFILE_FLOWER")" >/dev/null
        if [ $? -eq 0 ] ;
        then
            echo ">> Flower is already running!"
            return 1
        fi
        rm -f $PIDFILE_FLOWER
    fi

    echo ">> Starting Flower"
    $FLOWER_CMD > $LOGFILE 2>&1 &
    PID=$!
    echo $PID > "${PIDFILE_FLOWER}"
    echo ">> Flower is running!"
}

function stop_flower() {
    cddir
    if [ -e "${PIDFILE_FLOWER}" ] ;
    then
        PID=`cat $PIDFILE_FLOWER`
        ps -p $PID >/dev/null
        if [ $? -ne 0 ] ;
        then
            echo ">> Flower is already stopped!"
            rm -f $PIDFILE_FLOWER
            return 1
        fi
        kill -TERM $PID
        echo "TERM signal issued to Flower" >> $LOGFILE
        echo ">> Waiting for the Flower to stop"
        while kill -0 "$PID" >/dev/null 2>&1 ; do
            sleep 0.5
        done
        rm -f $PIDFILE_FLOWER
        return 0
    else
        echo ">> No pidfile present, Flower probably not running"
        return 1
    fi
}


function start_sprout() {
    start_logserver
    start_memcached
    start_gunicorn
    start_worker
    start_flower
    start_beat
}

function stop_sprout() {
    stop_beat
    stop_worker
    stop_flower
    stop_gunicorn
    stop_memcached
    stop_logserver
}

function restart_sprout() {
    stop_sprout
    start_sprout
}

function backup_before_update() {
    echo ">> Backing up"
    cddir
    [ ! -e "${BACKUP_DIR}" ] && {
        echo ">>> Creating the backup directory"
        mkdir "${BACKUP_DIR}"
        cd "${BACKUP_DIR}" || exit
        git init .
        cddir
    }
    echo ">>> Copying logs"
    cp -R ./log "${BACKUP_DIR}"
    echo ">>> Setting date"
    date "+%Y-%m-%d %H:%M:%S" > "${BACKUP_DIR}/backup.date"
    echo ">>> Getting the current hash"
    git rev-parse HEAD > "${BACKUP_DIR}/backup.hash"
    echo ">> Dumping the database"
    ./manage.py dumpdata --format=yaml --natural-foreign -e contenttypes -e sessions.Session -e auth.Permission > "${BACKUP_DIR}/database.yaml"
    echo ">>> Storing the backup in git"
    cd "${BACKUP_DIR}" || exit
    git add .
    git commit -a -m "`cat ${BACKUP_DIR}/backup.date`, `cat ${BACKUP_DIR}/backup.hash`"
    cddir
}


function update_sprout() {
    cddir
    if [ -e .update-running ] ;
    then
        echo "Another update process is already running!"
        echo "If that is an artifact after some hickup, remove .update-running file"
        exit 5
    fi
    touch .update-running
    echo "> Beginning update"
    echo "--- Update begun at `date` ---" >> $UPDATE_LOG
    backup_before_update
    clearpyc
    stop_beat
    rm -f celerybeat-schedule
    echo "> Fetching updates"
    git checkout master  >> $UPDATE_LOG 2>&1
    git pull origin master  >> $UPDATE_LOG 2>&1
    echo "> Installing requirements"
    pip install -U pip
    pushd ..
    PYCURL_SSL_LIBRARY=nss pip install -Ur requirements.txt >> $UPDATE_LOG
    popd
    PYCURL_SSL_LIBRARY=nss pip install -Ur requirements.txt >> $UPDATE_LOG
    clearpyc
    echo "> Collecting static files"
    ./manage.py collectstatic --noinput >> $UPDATE_LOG
    echo "> Pulling the YAMLs"
    update_yamls
    if migrations_needed ;
    then
        echo "> Stopping processes"
        stop_flower
        stop_worker
        stop_gunicorn
        echo "> Running migrations"
        ./manage.py migrate >> $UPDATE_LOG
        echo "> Starting processes"
        start_gunicorn
        start_worker
        start_flower
    else
        # Easy case
        echo "> Reloading Sprout"
        reload_gunicorn
        stop_worker
        stop_flower
        start_worker
        start_flower
    fi
    start_beat
    start_logserver
    echo "--- Update finished at `date` ---" >> $UPDATE_LOG
    rm .update-running
}

function reload_sprout() {
    cddir
    echo "> Starting reload"
    clearpyc
    stop_beat
    rm -f celerybeat-schedule
    reload_gunicorn
    stop_flower
    stop_worker
    start_worker
    start_flower
    start_beat
    echo "> Reload finished"
}


function sprout_needs_update() {
    if needs_update ;
    then
        echo "needs update"
        exit 1
    else
        echo "up-to-date"
        exit 0
    fi
}

case "${ACTION}" in
    gunicorn-start) start_gunicorn ;;
    beat-start) start_beat ;;
    worker-start) start_worker ;;
    flower-start) start_flower ;;
    memcached-start) start_memcached ;;
    logserver-start) start_logserver ;;
    gunicorn-stop) stop_gunicorn ;;

    beat-stop) stop_beat ;;
    worker-stop) stop_worker ;;
    flower-stop) stop_flower ;;
    memcached-stop) stop_memcached ;;
    logserver-stop) stop_logserver ;;

    start) start_sprout ;;
    stop) stop_sprout ;;
    restart) restart_sprout ;;
    reload) reload_sprout ;;

    update) update_sprout ;;
    check-update) sprout_needs_update ;;
    yaml-update) update_yamls ;;
    backup) backup_before_update ;;
    *) echo "Usage: ${0} start|{gunicorn,beat,worker,flower,memcached,logserver}-start|stop|{gunicorn,beat,worker,flower,memcached, logserver}-stop|restart|check-update|update|reload" ;;
esac
