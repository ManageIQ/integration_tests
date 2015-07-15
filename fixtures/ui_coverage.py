"""UI Coverage for a CFME/MIQ Appliance

Usage
-----

``py.test --ui-coverage``

General Notes
-------------
simplecov can merge test results, but doesn't appear to like working in a
multi-process environment. Specifically, it clobbers its own results when running
simultaneously in multiple processes. To solve this, each process records its
output to its own directory (configured in coverage_hook). All of the
individual process' results are then manually merged (coverage_merger) into one
big json result, and handed back to simplecov which generates the compiled html
(for humans) and rcov (for jenkins) reports.

thing_toucher makes a best-effort pass at requiring all of the ruby files in
the rails root, as well as any external MIQ libs/utils outside of the rails
root (../lib and ../lib/util). This makes sure files that are never
required still show up in the coverage report.

Workflow Overview
-----------------

Pre-testing (``pytest_configure`` hook):

1. Add ``Gemfile.dev.rb`` to the rails root, then run bundler to install simplecov
   and its dependencies.
2. Install and require the coverage hook (copy ``coverage_hook`` to config/, add
   require line to the end of ``config/boot.rb``)
3. Restart EVM (Rudely) to start running coverage on the appliance processes:
   ``killall -9 ruby; service evmserverd start``
4. TOUCH ALL THE THINGS (run ``thing_toucher.rb`` with the rails runner).
   Fork this process off and come back to it later

Post-testing (``pytest_unconfigure`` hook):

1. Poll ``thing_toucher`` to make sure it completed; block if needed.
2. Stop EVM, but nicely this time so the coverage atexit hooks run:
   ``service evmserverd stop``
3. Run ``coverage_merger.rb`` with the rails runner, which compiles all the individual process
   reports and runs coverage again, additionally creating an rcov report
4. Pull the coverage dir back for parsing and archiving
5. For fun: Read the results from ``coverage/.last_run.json`` and print it to the test terminal/log

Post-testing (e.g. ci environment):
1. Use the generated rcov report with the ruby stats plugin to get a coverage graph
2. Zip up and archive the entire coverage dir for review

"""
import subprocess
from threading import Thread

import pytest
from py.error import ENOENT
from py.path import local

from fixtures.pytest_store import store
from utils import conf, version
from utils.log import create_sublogger
from utils.path import conf_path, log_path, scripts_data_path
from utils.wait import wait_for

# paths to all of the coverage-related files

# on the appliance
#: Corresponds to Rails.root in the rails env
rails_root = local('/var/www/miq/vmdb')
#: coverage root, should match what's in the coverage hook and merger scripts
appliance_coverage_root = rails_root.join('coverage')

# local
coverage_data = scripts_data_path.join('coverage')
gemfile = coverage_data.join('Gemfile.dev.rb')
coverage_hook = coverage_data.join('coverage_hook.rb')
coverage_merger = coverage_data.join('coverage_merger.rb')
thing_toucher = coverage_data.join('thing_toucher.rb')
coverage_output_dir = log_path.join('coverage')
coverage_results_archive = coverage_output_dir.join('coverage-results.tgz')
coverage_appliance_conf = conf_path.join('.ui-coverage')

# This is set in sessionfinish, and should be reliably readable
# in post-yield sessionfinish hook wrappers and all hooks thereafter
ui_coverage_percent = None


def _thing_toucher_async(ssh_client):
    # for use in a subprocess to kick off the thing toucher
    result = ssh_client.run_rails_command('thing_toucher.rb', timeout=0)
    return result.rc == 0


def clean_coverage_dir():
    try:
        coverage_output_dir.remove(ignore_errors=True)
    except ENOENT:
        pass
    coverage_output_dir.ensure(dir=True)


def manager():
    return store.current_appliance.coverage


# you probably don't want to instantiate this manually
# instead, use the "manager" function above
class CoverageManager(object):
    def __init__(self, ipappliance):
        self.ipapp = ipappliance
        if store.slave_manager:
            sublogger_name = '{} coverage'.format(store.slave_manager.slaveid)
        else:
            sublogger_name = 'coverage'
        self.log = create_sublogger(sublogger_name)

    @property
    def collection_appliance(self):
        # if parallelized, this is decided in sessionstart and written to the conf
        if store.parallelizer_role == 'slave':
            from utils.appliance import IPAppliance
            return IPAppliance(conf['.ui-coverage']['collection_appliance'])
        else:
            # otherwise, coverage only happens on one appliance
            return store.current_appliance

    def print_message(self, message):
        self.log.info(message)
        message = 'coverage: {}'.format(message)
        if store.slave_manager:
            store.slave_manager.message(message)
        elif store.parallel_session:
            store.parallel_session.print_message(message)
        else:
            store.terminalreporter.write_sep('-', message)

    def install(self):
        self.print_message('installing')
        self._install_simplecov()
        self._install_coverage_hook()
        self.ipapp.restart_evm_service(rude=True)
        self._touch_all_the_things()
        self.ipapp.wait_for_web_ui()

    def collect(self):
        self.print_message('collecting reports')
        self._stop_touching_all_the_things()
        self._collect_reports()
        self.ipapp.restart_evm_service(rude=False)

    def merge(self):
        self.print_message('merging reports')
        try:
            self._retrieve_coverage_reports()
            # If the appliance runs out of memory, these can take *days* to complete,
            # so for now we'll just collect the raw coverage data and figure the merging
            # out later
            # self._merge_coverage_reports()
            # self._retrieve_merged_reports()
        except Exception as exc:
            self.log.error('Error merging coverage reports')
            self.log.exception(exc)
            self.print_message('merging reports failed, error has been logged')

    def _install_simplecov(self):
        self.log.info('Installing coverage gem on appliance')
        self.ipapp.ssh_client.put_file(gemfile.strpath, rails_root.strpath)

        # gem install for more recent downstream builds
        def _gem_install():
            self.ipapp.ssh_client.run_command(
                'gem install --install-dir /opt/rh/cfme-gemset/ -v0.9.2 simplecov')

        # bundle install for old downstream and upstream builds
        def _bundle_install():
            self.ipapp.ssh_client.run_command('yum -y install git')
            self.ipapp.ssh_client.run_command('cd {}; bundle'.format(rails_root))
        version.pick({
            version.LOWEST: _bundle_install,
            '5.4': _gem_install,
            version.LATEST: _bundle_install,
        })()

    def _install_coverage_hook(self):
        # Clean appliance coverage dir
        self.ipapp.ssh_client.run_command('rm -rf {}'.format(
            appliance_coverage_root.strpath))
        # Put the coverage hook in the miq lib path
        self.ipapp.ssh_client.put_file(coverage_hook.strpath, rails_root.join(
            '..', 'lib', coverage_hook.basename).strpath)
        replacements = {
            'require': r"require 'coverage_hook'",
            'config': rails_root.join('config').strpath
        }
        # grep/echo to try to add the require line only once
        # This goes in preinitializer after the miq lib path is set up,
        # which makes it so ruby can actually require the hook
        command_template = (
            'cd {config};'
            'grep -q "{require}" preinitializer.rb || echo -e "\\n{require}" >> preinitializer.rb'
        )
        x, out = self.ipapp.ssh_client.run_command(command_template.format(**replacements))
        return x == 0

    def _touch_all_the_things(self):
        self.log.info('Establishing baseline coverage by requiring ALL THE THINGS')
        # send over the thing toucher
        self.ipapp.ssh_client.put_file(
            thing_toucher.strpath, rails_root.join(
                thing_toucher.basename).strpath
        )
        # start it in an async thread so we can go on testing while this takes place
        t = Thread(target=_thing_toucher_async, args=[self.ipapp.ssh_client])
        t.daemon = True
        t.start()

    def _still_touching_all_the_things(self):
        return self.ipapp.ssh_client.run_command('pgrep -f thing_toucher.rb', timeout=10).rc == 0

    def _stop_touching_all_the_things(self):
        self.log.info('Waiting for baseline coverage generator to finish')
        # let the thing toucher finish touching all the things, it generally doesn't take more
        # than 10 minutes, so we'll be nice and give it 20
        wait_for(self._still_touching_all_the_things, fail_condition=True, num_sec=1200,
            message='check thing_toucher.rb on appliance')

    def _collect_reports(self):
        # restart evm to stop the proccesses and let the simplecov exit hook run
        self.ipapp.ssh_client.run_command('service evmserverd stop')
        # collect back to the collection appliance if parallelized
        if store.current_appliance != self.collection_appliance:
            self.print_message('sending reports to {}'.format(self.collection_appliance.address))
            self.ipapp.ssh_client.run_command('scp -o StrictHostKeyChecking=no '
                '-r /var/www/miq/vmdb/coverage/* '
                '{addr}:/var/www/miq/vmdb/coverage/'.format(
                    addr=self.collection_appliance.address),
                timeout=1800)

    def _retrieve_coverage_reports(self):
        # Before merging, archive and collect all the raw coverage results
        ssh_client = self.collection_appliance.ssh_client
        ssh_client.run_command('cd /var/www/miq/vmdb/;'
            'tar czf /tmp/ui-coverage-raw.tgz coverage/')
        ssh_client.get_file('/tmp/ui-coverage-raw.tgz', coverage_results_archive.strpath)

    def _merge_coverage_reports(self):
        # run the merger on the appliance to generate the simplecov report
        # This has been failing, presumably due to oom errors :(
        ssh_client = self.collection_appliance.ssh_client
        ssh_client.put_file(coverage_merger.strpath, rails_root.strpath)
        ssh_client.run_rails_command(coverage_merger.basename)

    def _retrieve_merged_reports(self):
        # Now bring the report back (tar it, get it, untar it)
        ssh_client = self.collection_appliance.ssh_client
        ssh_client.run_command('cd /var/www/miq/vmdb/coverage;'
            'tar czf /tmp/ui-coverage-results.tgz merged/')
        ssh_client.get_file('/tmp/ui-coverage-results.tgz', coverage_results_archive.strpath)
        subprocess.Popen(['/usr/bin/env', 'tar', '-xaf', coverage_results_archive.strpath,
            '-C', coverage_output_dir.strpath]).wait()


class UiCoveragePlugin(object):
    def pytest_configure(self, config):
        # cleanup cruft from previous runs
        if store.parallelizer_role != 'slave':
            clean_coverage_dir()
        coverage_appliance_conf.check() and coverage_appliance_conf.remove()

    def pytest_sessionstart(self, session):
        # master knows all the appliance URLs now, so name the first one as our
        # report recipient for merging at the end. Need to to write this out to a conf file
        # since all the slaves are going to use to to know where to ship their reports
        if store.parallelizer_role == 'master':
            collection_appliance_address = manager().collection_appliance.address
            conf.runtime['.ui-coverage']['collection_appliance'] = collection_appliance_address
            conf.save('.ui-coverage')

    @pytest.mark.hookwrapper
    def pytest_collection_finish(self):
        yield
        # Install coverage after collection finishes
        if store.parallelizer_role != 'master':
            manager().install()

    def pytest_sessionfinish(self, exitstatus):
        # Now master/standalone needs to move all the reports to an appliance for the source report
        if store.parallelizer_role != 'master':
            manager().collect()

        # for slaves, everything is done at this point
        if store.parallelizer_role == 'slave':
            return

        # on master/standalone, merge all the collected reports and bring them back
        manager().merge()

# TODO
# When the coverage reporting breaks out, we'll want to have this handy,
# so I'm commenting it out instead of outright deleting it :)
#         try:
#             global ui_coverage_percent
#             last_run = json.load(log_path.join('coverage', 'merged', '.last_run.json').open())
#             ui_coverage_percent = last_run['result']['covered_percent']
#             style = {'bold': True}
#             if ui_coverage_percent > 40:
#                 style['green'] = True
#             else:
#                 style['red'] = True
#             store.write_line('UI Coverage Result: {}%'.format(ui_coverage_percent),
#                 **style)
#         except Exception as ex:
#             logger.error('Error printing coverage report to terminal')
#             logger.exception(ex)


def pytest_addoption(parser):
    group = parser.getgroup('cfme')
    group.addoption('--ui-coverage', dest='ui_coverage', action='store_true', default=False,
        help="Enable setup and collection of ui coverage on an appliance")


def pytest_cmdline_main(config):
    # Only register the plugin worker if ui coverage is enabled
    if config.option.ui_coverage:
        config.pluginmanager.register(UiCoveragePlugin(), name="ui-coverage")
