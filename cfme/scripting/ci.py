"""
click commands for ci testing
"""
import click
import os
import subprocess
from utils import path


@click.group(help='Functions for test and ci related actions')
def main():
    pass


@main.command()
@click.pass_context
@click.option("--credentials-repo", envvar="CFME_CRED_REPO")
def fetch_credentials(ctx, credentials_repo):
    credentials_path = path.project_path.dirpath().join('cfme-qe-yamls')
    if credentials_path.check(dir=True):
        return subprocess.call(
            ['git', 'pull'],
            cwd=str(credentials_path),
            env=dict(os.environ, GIT_SSL_NO_VERIFY='true'),
        )
    else:
        if credentials_repo is None:
            ctx.fail("without an existing repo the credentials repo "
                     "needs to be passed explicitly")
        return subprocess.call(
            ['git', 'clone', str(credentials_repo), str(credentials_path)],
            env=dict(os.environ, GIT_SSL_NO_VERIFY='true'),
        )
