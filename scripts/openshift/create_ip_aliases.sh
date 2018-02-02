#!/bin/bash
start_ip=10.8.218.$1
end_ip=10.8.218.$2
submask='27'

ip_alias=0
for ip in {${start_ip}..${end_ip}}
do
  ip_alias=$((++ip_alias))
  cmd="/sbin/ifconfig enp3s0f0:${ip_alias} ${ip}/${submask}";
  echo "Running cmd ${cmd}";
  eval ${cmd};
done
