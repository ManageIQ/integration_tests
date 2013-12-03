#!/usr/bin/env python
# coding: utf-8

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#
# Description: CFME Migration
#
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


import logging
import time
import argparse
import subprocess as sub



parser = argparse.ArgumentParser(epilog=__doc__,formatter_class=argparse.RawDescriptionHelpFormatter)
parser.add_argument('--backupfile', dest='backupfile',help='backup file to be restored')
parser.add_argument('--script', help='script to restore the db')
parser.add_argument('--upgrdscript', help='v4 upgrade fix script')
parser.add_argument('--reboot',help = 'reboot the appliance',action="store_true")
args = parser.parse_args()


LOG_FILENAME = 'output.log'
logging.basicConfig(level=logging.DEBUG,
                    filename=LOG_FILENAME,
                    filemode='w')
logger = logging.getLogger('migration')


#Execute command
def run_command(cmd):
        logger.info('Running: %s' % cmd);
        process = sub.Popen(cmd,shell=True,stdout=sub.PIPE,stderr=sub.PIPE)
        output, error = process.communicate()
        if process.returncode != 0:
                logger.debug(error)
                raise Exception("%s: FAILED" % cmd);
                logger.info("%s: output value" % output);
        else:
                logger.info('SUCCESS')
	return output




#copy scripts
cpyscript =  "cp "+args.script+" /var/www/miq/vmdb/"
run_command(cpyscript)


#changedir and untar scripts
untar = "cd /var/www/miq/vmdb/;tar xvf "+args.script+"" 
run_command(untar)

#stop evm process
evmstop = 'service evmserverd stop'
run_command(evmstop)



#check pg connections and execute restore script
find_pgcount = 'psql -d vmdb_production -U root -c "SELECT count(*) from pg_stat_activity"' 
psql_output = run_command(find_pgcount)
count = psql_output.split("\n")[2].strip()
if count > 2:
    run_command("service postgresql92-postgresql restart")
    time.sleep(60)
    run_command("/var/www/miq/vmdb/backup_and_restore/miq_vmdb_background_restore "+args.backupfile+"  > restore.log")
    logger.info('Restore completed successfully')
else:
    run_command("cd /var/www/miq/vmdb/backup_and_restore/;./miq_vmdb_background_restore "+args.backupfile+" > restore.log")
    logger.info('Restore completed successfully')


#if states relation exists then truncate table
table_exists = 'psql -d vmdb_production -U root -c "SELECT EXISTS(SELECT 1 FROM information_schema.tables WHERE table_name = \'states\')" '
psql_output = run_command(table_exists)
table_output = psql_output.split("\n")[2].strip()
if "t" in table_output:
	truncate = 'psql -d vmdb_production -U root -c "truncate table states"'
	out = run_command(truncate)
else:
	logger.debug('Relation states does not exists')


#changedir and  run rake
run_command("cd /var/www/miq/vmdb;bin/rails r bin/rake db:migrate > rake.log")
logger.info('rake completed successfully')



#check db migrate status
run_command("cd /var/www/miq/vmdb;rake db:migrate:status > migratestatus")

#find version and if v4 run upgrade fixes
find_version = 'psql -d vmdb_production -U root -c "SELECT distinct (version) from miq_servers"'
psql_output = run_command(find_version)
version = psql_output.split("\n")[2].strip()
if "4." in version:
        cpyscript =  "cp "+args.upgrdscript+" /var/www/miq/vmdb/tools/"
	run_command(cpyscript)
	untar = "cd /var/www/miq/vmdb/tools/;tar xvf "+args.upgrdscript+""
	run_command(untar)
	run_command("cd /var/www/miq/vmdb;bin/rails r tools/v4_upgrade_fixes.rb > upgrade.log")
	logger.info('Upgrade completed successfully')
else:
	logger.info("%s: version value" % version);



#check for REGION
find_region = 'psql -d vmdb_production -U root -c "select region from users"' 
psql_output = run_command(find_region)
region_output = psql_output.split("\n")[2].strip()
f = open('/var/www/miq/vmdb/REGION', 'w')
f.write(region_output)
f.close()

#reboot
if args.reboot:
	logger.info('Rebooting the appliance')
        run_command('reboot')
else:
        logger.info('A reboot is required')

