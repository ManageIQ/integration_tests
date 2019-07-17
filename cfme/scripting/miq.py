import click

from artifactor.__main__ import main as art_main
from cfme.scripting.appliance import main as app_main
from cfme.scripting.bz import main as bz_main
from cfme.scripting.conf import main as conf_main
from cfme.scripting.ipyshell import main as shell_main
from cfme.scripting.polarion import main as polarion_main
from cfme.scripting.requirement import main as requirement_main
from cfme.scripting.setup_env import main as setup_main
from cfme.scripting.sprout import main as sprout_main
from cfme.utils.dockerbot.sel_container import main as sel_con_main
from cfme.utils.release import main as rel_main


@click.group()
def miq():
    pass


miq.add_command(app_main, name="appliance")
miq.add_command(art_main, name="artifactor-server")
miq.add_command(bz_main, name="bz")
miq.add_command(conf_main, name="conf")
miq.add_command(polarion_main, name="polarion")
miq.add_command(rel_main, name="release")
miq.add_command(requirement_main, name="requirement")
miq.add_command(sel_con_main, name="selenium-container")
miq.add_command(setup_main, name="setup-env")
miq.add_command(shell_main, name="shell")
miq.add_command(sprout_main, name="sprout")

if __name__ == '__main__':
    miq()
