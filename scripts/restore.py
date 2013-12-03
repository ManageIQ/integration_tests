#!/usr/bin/env python
# coding: utf-8

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#
# Description: CFME Migration
# Author: Aziza Karol <akarol@redhat.com>
# Copyright (C) 2013  Red Hat
# see file 'COPYING' for use and warranty information
#
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


import logging
import os
import commands
import time
import subprocess as sub


LOG_FILENAME = 'output.log'
BACKUP_FILE  = 'miq_dumpall_vmdb_production_20131104_154937_5.1_dump.gz'
BACKUP_PATH = "/root/" + BACKUP_FILE
SCRIPT = "cmfe_5.2_vmdb_backup_and_restore_scripts_20131031_153100.tgz"
SCRIPT_PATH = "/root/" + SCRIPT
FOUND = 0

logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s %(levelname)s %(message)s',
                    filename=LOG_FILENAME,
                    filemode='w')


#Execute command
def run_command(cmd):
        logging.info('Running: %s' % cmd);
        output = sub.Popen(cmd,shell=True,stdout=sub.PIPE,stderr=sub.PIPE).communicate()[0]
        return output


#copy backup file at location /opt/rh/postgresql92/root/var/lib/pgsql/
if (int(run_command("cp  "+BACKUP_PATH+" /opt/rh/postgresql92/root/var/lib/pgsql/;echo $?")) == FOUND ):
    logging.info('SUCCESS')
else:
    logging.info('FAILED')


#copy backupfile name to a file
os.system('touch  /var/www/miq/vmdb/log/miq_last_backup_file_name')
f = open('/var/www/miq/vmdb/log/miq_last_backup_file_name', 'w')
f.write('/opt/rh/postgresql92/root/var/lib/pgsql/' + BACKUP_FILE)
f.close()


#make backup and restore dir
makedir  = 'mkdir -p /var/www/miq/vmdb/backup_and_restore'
run_command(makedir)

#copy scripts
run_command("cp "+SCRIPT_PATH+" /var/www/miq/vmdb/backup_and_restore")


#changedir and untar scripts
untar = "cd /var/www/miq/vmdb/backup_and_restore;tar xvf "+SCRIPT+"" 
run_command(untar)

#stop evm process
evmstop = '/etc/init.d/evmserverd stop'
run_command(evmstop)


#check pg connections and execute restore script
os.system('rm -rf pgcount')                 #remove any previously existing file
find_pgcount = 'psql -d vmdb_production -U root -c "SELECT count(*) from pg_stat_activity" -L pgcount | gawk -f find_pgcount.awk  pgcount'
count = run_command(find_pgcount)
print count
if count > 2:
    run_command("service postgresql92-postgresql stop")
    run_command("service postgresql92-postgresql start")
    time.sleep(60)
    if (int(run_command("/var/www/miq/vmdb/backup_and_restore/miq_vmdb_background_restore > restore.log;echo $?")) == FOUND ):
    	logging.info('SUCCESS')
    else:
    	logging.info('FAILED')
else:
    print "pgconnection less then two"
    if (int(run_command("cd /var/www/miq/vmdb/backup_and_restore;./miq_vmdb_background_restore > restore.log;echo $?")) == FOUND ):
   	 logging.info('SUCCESS')
    else:
    	logging.info('FAILED')
 


#truncate table states
truncate = 'psql -d vmdb_production -U root -c "truncate table states"'
out = run_command(truncate)


#changedir and  run rake
if (int(run_command("cd /var/www/miq/vmdb;bin/rails r bin/rake db:migrate > rake.log;echo $?")) == FOUND ):
    logging.info('SUCCESS')
else:
    logging.info('FAILED')


#check db migrate status
if (int(run_command("cd /var/www/miq/vmdb;rake db:migrate:status > migratestatus;echo $?")) == FOUND ):
    logging.info('SUCCESS')
else:
    logging.info('FAILED')


#check for REGION
os.system('rm -rf region region_value')
find_region = 'psql -d vmdb_production -U root -c "select region from users" -L region | gawk -f find_region.awk region > region_value'
out = run_command(find_region)
os.system('cp region_value /var/www/miq/vmdb/REGION')


#reboot
logging.info('Rebooting the system')
#os.system('reboot')


