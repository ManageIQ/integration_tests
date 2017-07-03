import click

template = """[update-{0}]
name=update-url-{0}
baseurl={1}
enabled=1
gpgcheck=0\n\n"""


@click.command(help="Assist in generating update repo file")
@click.argument('filename')
@click.option('--output', default="yum.repo", help="output filename")
def main(filename, output):
    """Assist in generating update repo file"""
    print filename
    print
    with open(filename) as f:
        lines = f.readlines()
    c = 0
    with open(output, 'w') as f:
        for line in lines:
            if line.strip():
                url = line[line.find("http"):].strip()
                print template.format(c, url)
                f.write(template.format(c, url))
                c += 1


if __name__ == "__main__":
    main()
