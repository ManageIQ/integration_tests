import click
from artifactor.__main__ import main as art_main
from cfme.scripting.appliance import main as app_main
from cfme.scripting.conf import main as conf_main
from cfme.scripting.ipyshell import main as shell_main
from cfme.scripting.setup_env import main as setup_main
from cfme.scripting.sprout import main as sprout_main

from scripts.dockerbot.sel_container import main as sel_con_main
from scripts.release import main as rel_main


@click.group()
def cli():
    pass


cli.add_command(app_main, name="appliance")
cli.add_command(sel_con_main, name="selenium-container")
cli.add_command(art_main, name="artifactor-server")
cli.add_command(rel_main, name="release")
cli.add_command(shell_main, name="shell")
cli.add_command(conf_main, name="conf")
cli.add_command(sprout_main, name="sprout")
cli.add_command(setup_main, name="setup-env")

if __name__ == '__main__':
    cli()
