#!/bin/bash
if [ ! $# == 2 ]; then
  echo "Usage: ./perf_collect_logs.sh <directory> <log-name-prefix>"
  exit
fi
logdir=$1
prefix=$2

rm -rf ${logdir}${prefix}.perf.log.gz

cd $logdir || exit
for file in `ls ${prefix}.log-* | sort -V`
do
  echo "Processing $file"
  cp ${file} ${file}-2.gz
  gunzip ${file}-2.gz
  cat ${file}-2 >> ${logdir}${prefix}.perf.log
  rm -rf ${file}-2
done

cat ${logdir}${prefix}.log >> ${logdir}${prefix}.perf.log
gzip ${logdir}${prefix}.perf.log
