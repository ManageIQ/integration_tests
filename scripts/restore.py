#!/usr/bin/env python
# coding: utf-8

import logging
import time
from optparse import OptionParser
import subprocess as sub

parser = OptionParser()
parser.add_option('--backupfile', help='backup file to be restored')
parser.add_option('--scripts', help='scripts tarball to restore the db')
parser.add_option('--fixscripts', help='v4 upgrade fix script tarball')
parser.add_option('--outputdir', help='directory to dump output files to')
parser.add_option('--evmstart', help='start evm afterwards', action="store_true")
(options, args) = parser.parse_args()

# Setup logger
LOG_FILENAME = 'output.log'
logging.basicConfig(level=logging.DEBUG,
                    filename=LOG_FILENAME,
                    filemode='w')
logger = logging.getLogger('migration')


#Execute command
def run_command(cmd):
    logger.info('Running: %s' % cmd)
    process = sub.Popen(cmd, shell=True, stdout=sub.PIPE, stderr=sub.PIPE)
    output, error = process.communicate()
    logger.info("\nSTDOUT:\n%s" % output)
    if process.returncode != 0:
        logger.debug(error)
        raise Exception("%s: FAILED" % cmd)
    else:
        logger.info('SUCCESS')
    return output

#copy scripts
run_command("cp " + options.scripts + " /var/www/miq/vmdb/")

#changedir and untar scripts
run_command("cd /var/www/miq/vmdb/;tar xvf " + options.scripts)

#stop evm process
run_command('service evmserverd stop')

#check pg connections and execute restore script
psql_output = run_command('psql -d vmdb_production -U root -c ' +
    '"SELECT count(*) from pg_stat_activity"')
count = psql_output.split("\n")[2].strip()
if count > 2:
    run_command("service postgresql92-postgresql restart")
    time.sleep(60)
run_command("cd /var/www/miq/vmdb/backup_and_restore/;./miq_vmdb_background_restore " +
    options.backupfile + " > /tmp/restore.log")
logger.info('Restore completed successfully')
run_command('cat /tmp/restore.log')

#if states relation exists then truncate table
psql_output = run_command('psql -d vmdb_production -U root -c ' +
    '"SELECT EXISTS(SELECT 1 FROM information_schema.tables WHERE table_name = \'states\')" ')
table_output = psql_output.split("\n")[2].strip()
if "t" in table_output:
    out = run_command('psql -d vmdb_production -U root -c "truncate table states"')
else:
    logger.debug('Relation states does not exists')

#changedir and  run rake
run_command("cd /var/www/miq/vmdb;bin/rails r bin/rake db:migrate > /tmp/rake.log")
logger.info('rake completed successfully')
run_command('cat /tmp/rake.log')

#check db migrate status
run_command("cd /var/www/miq/vmdb;rake db:migrate:status > /tmp/migratestatus.out")
run_command('cat /tmp/migratestatus.out')

#find version and if v4 run upgrade fixes
psql_output = run_command('psql -d vmdb_production -U root -c ' +
    '"SELECT distinct (version) from miq_servers"')
version = psql_output.split("\n")[2].strip()
if "4." in version:
    run_command("cp " + options.fixscripts + " /var/www/miq/vmdb/tools/")
    run_command("cd /var/www/miq/vmdb/tools/;tar xvf " + options.fixscripts)
    run_command("cd /var/www/miq/vmdb;bin/rails r tools/v4_upgrade_fixes.rb > /tmp/upgrade.log")
    logger.info('Upgrade completed successfully')
    run_command('cat /tmp/upgrade.log')
else:
    logger.info("%s: version value" % version)

#check for REGION
psql_output = run_command('psql -d vmdb_production -U root -c "select region from users"')
region_output = psql_output.split("\n")[2].strip()
logger.info("%s: region value" % region_output)
f = open('/var/www/miq/vmdb/REGION', 'w')
f.write(region_output)
f.close()

# reset user passwords
psql_output = run_command('psql -d vmdb_production -U root -c "update users set password_digest ' +
    '= \'\$2a\$10\$cyjSQmNq6zf9LuyWIfzSF\.95Hxuxv3KqDQMGFiRxIxacWD0uFIQEi\'"')

# start evm now?
if options.evmstart:
    logger.info('Starting evm server')
    run_command('service evmserverd start')
