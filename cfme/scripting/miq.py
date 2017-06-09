import click
from artifactor.__main__ import main as art_main
from scripts.dockerbot.sel_container import main as sel_con_main


@click.group()
def cli():
    pass


cli.add_command(sel_con_main, name="selenium-container")
cli.add_command(art_main, name="artifactor-server")

if __name__ == '__main__':
    cli()
