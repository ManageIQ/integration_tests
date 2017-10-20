"""
click commands for ci testing
"""
import sys
import os
import subprocess
import contextlib
from functools import partial
import re

import click
from click import secho
from cfme.utils import conf
from cfme.utils import path
from cfme.utils import safe_string
from cfme.utils.trackerbot import post_task_result
from cfme.utils.wait import wait_for

from . import quickstart

GIT_NO_SSL = dict(GIT_SSL_NO_VERIFY='true')


def qe_yaml_path(path):
    return path.dirpath().join('cfme-qe-yamls')


def appliances_configured():
    return 'appliances:' in path.conf_path.join('env.local.yaml').read()


@contextlib.contextmanager
def managed_miq_sprout_checkout():
    """contextmanager to invoke miq sprout checkout

    it presumes all configuration is passed in the environment
    """
    checkout_process = subprocess.Popen(['miq', 'sprout', 'checkout'])
    try:
        wait_for(appliances_configured,
                 delay="10s", timeout="5m")
        yield
    finally:
        checkout_process.kill()
        checkout_process.wait()


@click.group(help='Functions for test and ci related actions')
def main():
    pass


def do(command, cwd=None, extra_env=None,  shell=False, **kwargs):
    """convenience to invoke subprocesses

    Args:
        command: the command to invoke
        cwd: the expected working directory
        extra_env: overrides for environment variables
        shell: same as for call
    """
    if extra_env:
        extra_env = {k: str(v) for k, v in extra_env.items() if v is not None}
        kwargs['env'] = dict(kwargs.get('env') or os.environ, **extra_env)
    if not shell:
        command = list(map(str, command))

    secho(str(command))
    ret = subprocess.call(command, cwd=cwd and str(cwd), shell=shell, **kwargs)
    if ret:
        click.echo("{!r} failed with {!r}".format(command, ret))
        sys.exit(ret)


@main.command()
@click.pass_context
@click.option("--credentials-repo", envvar="CFME_CRED_REPO")
def fetch_credentials(ctx, credentials_repo):
    """
    fetch the yaml credentials based on the config repo
    """
    credentials_path = qe_yaml_path(path.project_path)
    secho("updating credentials", fg="yellow")
    try:
        if credentials_path.check(dir=True):
            return do(
                ['git', 'pull'],
                cwd=credentials_path,
                extra_env=GIT_NO_SSL,
            )
        else:
            if credentials_repo is None:
                sys.exit("without an existing repo the credentials repo "
                         "needs to be passed explicitly")
            return do(
                ['git', 'clone', credentials_repo, credentials_path],
                extra_env=GIT_NO_SSL,
            )
    finally:
        quickstart.link_config_files('../cfme-qe-yamls/complete/', 'conf')


@main.command()
@click.argument('commit')
def verify_commit(commit):
    """
    fetches the configured pgp keys and verifies a git commit against them

    args:
        commit: the git commit to be verified
    """

    conf.clear()  # reload config
    key_list = [key.replace(' ', '') for key in conf.gpg['allowed_keys']]
    # TODO: getthe blunt work of this somewhere else
    do(['gpg2', '--recv-keys'] + key_list)
    logfile = path.log_path.join('gpg_verify.log')
    secho("verify commit")
    try:
        with logfile.open('wb') as fp:
            do(['git', 'verify-commit', commit, '--raw'], stderr=fp)
        output = logfile.read()
    finally:  # ensure we print  on failure
        output = logfile.read()
        secho(output)
    if 'GOODSIG' in output:
        gpg = re.findall('VALIDSIG ([A-F0-9]+)', output)[0]
        click.echo(gpg)
        if gpg in key_list:
            secho("Good sig and match for {}".format(gpg))
            return
    secho("Bad Sig")
    sys.exit(127)


@main.command()
@click.pass_context
@click.option("--cfme-repo", envvar="CFME_REPO", required=True)
@click.option("--cfme-pr", envvar="CFME_PR", default=None)
@click.option('--branch', envvar="BRANCH", default=None)
@click.option('--base-branch', envvar='BASE_BRANCH', default='master')
@click.option('--verify/--no-verify', default=True)
def prepare_workdir_checkout(ctx, cfme_repo, cfme_pr,
                             branch, base_branch, verify):
    secho("preparing checkout", fg="yellow")
    extra_env = {
        'CFME_PR': cfme_pr,
        'CFME_REPO': cfme_repo,
        'BASE_BRANCH': base_branch,
        'BRANCH': branch,
    }
    for k, v in extra_env.items():
        if v is not None:
            secho("  {}: {}".format(k, v))
    pdo = partial(do, shell=True, extra_env=extra_env)

    if not cfme_repo:
        ctx.fail("missing repo, failing")
    pdo('git remote add repo_under_test "$CFME_REPO"')
    if cfme_pr is not None:
        secho("preparing pr merge", fg="yellow")
        pdo('git fetch repo_under_test'
            ' "+refs/heads/$BASE_BRANCH:refs/repo_under_test/$BASE_BRANCH"')
        pdo('git fetch repo_under_test'
            ' +refs/pull/"$CFME_PR"/head:refs/heads/pr-"$CFME_PR"')
        if verify:
            ctx.invoke(verify_commit, commit='pr-{}'.format(cfme_pr))
        pdo('git checkout pr-$CFME_PR')
        pdo('git merge --no-ff --no-edit repo_under_test/$BASE_BRANCH')

    elif branch is not None:
        secho("preparing branch under test", fg="yellow")
        pdo('git fetch repo_under_test "+refs/heads/$BRANCH:refs/repo_under_test/$BRANCH"')
        pdo('git checkout "repo_under_test/$BRANCH"')
    else:
        ctx.fail("branch or pr needed to prep workdir")


CONFIGFILE_TEMPLATE = """
base_url: {appliance}
browser:
    webdriver_wharf: {wharf}
    webdriver_options:
        keep_alive: True
        desired_capabilities:
            platform: LINUX
            browserName: {browser}
artifactor:
    per_run: test #test, run, None
    reuse_dir: True
    squash_exceptions: True
    threaded: True
    server_address: 127.0.0.1
    server_enabled: True
    plugins:
        logger:
            enabled: True
            plugin: logger
            level: DEBUG
        filedump:
            enabled: True
            plugin: filedump
        reporter:
            enabled: True
            plugin: reporter
            only_failed: True

mail_collector:
    ports:
        smtp: {smtp}
        json: {json}

"""


@main.command()
@click.option("--browser", envvar="BROWSER")
@click.option("--wharf", envvar="WHARF", required=True)
@click.option('--appliance', envvar="APPLIANCE", required=True)
@click.option('--json', envvar="JSON", required=True)
@click.option('--smtp', envvar="SMTP", required=True)
def prepare_workdir_configfiles(browser, wharf, appliance, json, smtp):
    configfile = path.conf_path.join('env.local.yaml')
    if configfile.check(file=True):
        sys.exit("env.local.yaml exists - aborting automated overwrite")

    configfile.write(CONFIGFILE_TEMPLATE.format(
        browser=browser,
        wharf=wharf,
        json=json,
        smtp=smtp,
        appliance=appliance,
    ), ensure=True)


@main.command()
def run_tests(pytest_command):
    sys.exit(subprocess.call(pytest_command, shell=True))


@main.command()
@click.option("--credentials-repo", envvar="CFME_CRED_REPO")
@click.option("--cfme-repo", envvar="CFME_REPO", required=True)
@click.option("--cfme-pr", envvar="CFME_PR", default=None)
@click.option('--branch', envvar="BRANCH", default=None)
@click.option('--base-branch', envvar='BASE_BRANCH', default='master')
@click.option('--verify/--no-verify', default=True)
@click.option("--browser", envvar="BROWSER")
@click.option("--wharf", envvar="WHARF")
@click.option('--appliance', envvar="APPLIANCE")
@click.option('--json', envvar="JSON")
@click.option('--smtp', envvar="SMTP")
@click.option('--use-sprout', envvar="USE_SPROUT", default="no", type=click.Choice(['yes', 'no']))
@click.argument('pytest_command', envvar='PYTEST')
@click.pass_context
def full(ctx,
         credentials_repo,
         cfme_repo, cfme_pr, branch, base_branch, verify,
         browser, wharf, appliance, json, smtp,
         pytest_command, use_sprout):
    ctx.invoke(fetch_credentials,
               credentials_repo=credentials_repo)
    ctx.invoke(prepare_workdir_checkout,
               cfme_pr=cfme_pr, cfme_repo=cfme_repo,
               branch=branch, base_branch=base_branch,
               verify=verify)
    ctx.invoke(prepare_workdir_configfiles,
               browser=browser, wharf=wharf,
               appliance=appliance,
               json=json, smtp=smtp)

    run_quickstart()

    if use_sprout == 'yes':
        with managed_miq_sprout_checkout():
            ctx.invoke(run_tests, pytest_command=pytest_command)
    else:
        ctx.invoke(run_tests, pytest_command=pytest_command)


def run_quickstart():
    """runs quickstart against the current environment
    """
    quickstart.run_for_current_env()
    import sys
    sys.stdout.flush()
    sys.stderr.flush()


@main.command()
@click.option('--logfile', default=str(path.log_path / 'setup.txt'))
@click.argument('extra_args', nargs=-1)
@click.option('--post-task', default=None, envvar="POST_TASK")
def run_logged(logfile, extra_args, post_task):
    tee = subprocess.Popen(
        ['tee', '-a', logfile],
        stdin=subprocess.PIPE,
    )
    result = subprocess.call(
        ['miq', 'ci', 'full'] + list(extra_args),
        stdout=tee.stdin,
        stderr=tee.stdin,
    )
    result_name = 'passed' if result in (0, 5) else 'failed'

    if post_task:
        with open(logfile) as fp:
            setup_data = fp.read()

        try:

            with path.log_path.join("coverage_result.txt").open() as f:
                coverage_data = f.read().strip("\n")
            coverage = float(coverage_data)
        except Exception:
            coverage = 0.0
        conf.clear()  # reset all configuration
        post_task_result(
            post_task, result_name,
            safe_string(setup_data), coverage)
    sys.exit(0 if result_name == 'passed' else 1)
