#!/usr/bin/env bash
find . -name \*.pyc -delete

[ -e ./.env ] && . ./.env

redis-server --port ${REDIS_PORT:-6379} &
REDSRV=$!

sleep 5
redis-cli -p ${REDIS_PORT:-6379} FLUSHDB
redis-cli -p ${REDIS_PORT:-6379} FLUSHALL

kill -TERM $REDSRV

rm -f celerybeat-schedule
rm -rf appliances/migrations/0*
rm -f db.sqlite3
./manage.py makemigrations
./manage.py migrate
./manage.py createsuperuser

cd ../.. || exit
python -m compileall -f .
cd $OLDPWD || exit
