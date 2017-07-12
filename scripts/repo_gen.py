import click
import requests


template = """[update-{0}]
name=update-url-{0}
baseurl={1}
enabled=1
gpgcheck=0\n\n"""


def process_url(url):
    '''Pulls urls from a network file'''
    repo = requests.get(url)
    urls = repo.text.split("\n")
    ret_urls = []
    for url in urls:
        url = url[url.find("http"):].strip()
        ret_urls.append(url)
    return ret_urls


def build_file(urls):
    '''Builds a update.repo file based on the urls given'''
    file_string = ""
    c = 0
    for url in urls:
        if url:
            file_string = "{}{}".format(file_string, template.format(c, url))
            c += 1
    return file_string


@click.command(help="Assist in generating update repo file")
@click.option('--url', default=None, help='Specify a URL for downloading repo data')
@click.option('--filename', default=None, help='Specify a URL for downloading repo data')
@click.option('--output', default="update.repo", help="output filename")
def main(output, url, filename):
    """Assist in generating update repo file"""
    if url:
        urls = process_url(url)
        output_data = build_file(urls)
    elif filename:
        print "Can't do this right now"
    with open(output, 'w') as f:
        f.write(output_data)


if __name__ == "__main__":
    main()
