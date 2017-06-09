import click
from scripts.dockerbot.sel_container import main as sel_con_main


@click.group()
def cli():
    pass


cli.add_command(sel_con_main, name="selenium-container")

if __name__ == '__main__':
    cli()
