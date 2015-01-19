#!/usr/bin/env bash

git fetch origin >/dev/null 2>&1

git diff --name-only `git rev-parse master` `git rev-parse origin/master` | grep ^sprout/
RESULT=$?

if [ $RESULT -eq 0 ] ;
then
    echo "needs update"
else
    echo "up-to-date"
fi
