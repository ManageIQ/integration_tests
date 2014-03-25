#!/bin/bash

rm -rf /var/www/miq/vmdb/log/evm.total.log.gz

logdir=/var/www/miq/vmdb/log/
cd $logdir
for file in `ls evm.log-* | sort -V`
do
  echo "Processing $file"
  cp ${file} ${file}-2.gz
  gunzip ${file}-2.gz
  cat ${file}-2 >> /var/www/miq/vmdb/log/evm.total.log
  rm -rf ${file}-2
done

cat /var/www/miq/vmdb/log/evm.log >> /var/www/miq/vmdb/log/evm.total.log
gzip /var/www/miq/vmdb/log/evm.total.log
