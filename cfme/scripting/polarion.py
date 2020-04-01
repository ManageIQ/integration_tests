import click
import ruamel.yaml
from miq_version import Version
from ruamel.yaml.util import load_yaml_guess_indent

from cfme.utils.conf import credentials
from cfme.utils.log import add_stdout_handler
from cfme.utils.log import logger
from cfme.utils.path import conf_path


# constants for the polarion fields in yaml
POLARION_PROJECT_ID = 'polarion-project-id'
POLARION_URL = 'polarion_url'
XUNIT_HEADER = 'xunit_import_properties'
# these are under xunit import
TEMPLATE_ID = 'polarion-testrun-template-id'
TESTRUN_TITLE = 'polarion-testrun-title'
TESTRUN_ID = 'polarion-testrun-id'
GROUP_ID = 'polarion-group-id'

# Log to stdout too
add_stdout_handler(logger)


@click.group()
def main():
    """Function to populate polarion_tools.local.yaml

    This tool will take a polarion_tools.local.yaml template file, and populate empty field values
    with those derived from the given CLI options

    The default behavior is to write to polarion_tools.local.yaml in the conf_path directory
    cfme_testcases_upload will combine local.yaml and polarion_tools.yaml
    """
    pass


@main.command(
    'populate',
    help='Populate template with credentials and version based testrun data.'
         'Does NOT overwrite anything already set in the given template'
)
@click.option(
    '--template',
    help='YAML template to start with',
    default=conf_path.join('polarion_tools.local.yaml.template').strpath
)
@click.option(
    '--output',
    help='YAML file to write to',
    default=conf_path.join('polarion_tools.local.yaml').strpath
)
@click.option(
    '--credentials-key',
    help='Key for utils.conf.credentials used for polarion authentication',
    default='polarion-upload'
)
@click.option(
    '--vstring',
    help='version string that can be parsed for series and template selection'
)
@click.option(
    '--polarion-project-id',
    help='The polarion project ID to inject',
    default=None
)
@click.option(
    '--polarion-url',
    help='The polarion URL to inject',
    default=None
)
@click.option(
    '--template-format',
    help='The format for the test template, y-stream CFME digits is formatted in',
    default='ImportTestRunTemplate'
)
def populate(
    template,
    output,
    credentials_key,
    vstring,
    polarion_project_id,
    polarion_url,
    template_format,
):
    with open(template) as template_file:
        input_yaml, indent, block_indent = load_yaml_guess_indent(template_file)

    # first update credentials fields
    input_yaml['username'] = credentials[credentials_key]['username']
    input_yaml['password'] = credentials[credentials_key]['password']

    version = Version(vstring)
    replacement = None  # avoid UnboundLocal below
    # First handle xunit import nested values
    if XUNIT_HEADER not in input_yaml:
        logger.info('Skipping [%s] in polarion_tools.local.yaml template, missing',
                    XUNIT_HEADER)
    else:
        for KEY in [TEMPLATE_ID, GROUP_ID, TESTRUN_TITLE, TESTRUN_ID]:
            # replacement is different for each field
            if KEY == TEMPLATE_ID:
                # There's no error if the template_format doesn't have {}
                replacement = template_format.format(version.series().replace('.', ''))
            elif KEY in [TESTRUN_TITLE, TESTRUN_ID]:
                replacement = vstring.replace('.', '_')  # stupid polarion not allowing .
            elif KEY == GROUP_ID:
                # z-stream for group ID
                replacement = version.series(n=3)
            # now apply the replacement
            if input_yaml[XUNIT_HEADER].get(KEY, None) not in ['', None]:
                # Only set empty values, if the template has a value don't change it
                logger.info('SKIP [%s][%s] in polarion_tools.local.yaml template, already set',
                            XUNIT_HEADER, KEY)
            else:
                input_yaml[XUNIT_HEADER][KEY] = replacement
                logger.info('Setting key [%s] in polarion_tools.local.yaml template, to %s',
                        KEY, replacement)

    # top level keys not in xunit
    for KEY in [POLARION_URL, POLARION_PROJECT_ID]:
        if KEY == POLARION_PROJECT_ID:
            replacement = polarion_project_id
        elif KEY == POLARION_URL:
            replacement = polarion_url
        # check replacement and current value
        if replacement is None:
            logger.info('SKIP [%s] in polarion_tools.local.yaml template, no value passed', KEY)
            continue
        elif input_yaml.get(KEY, None) is not None:
            logger.info('SKIP [%s] in polarion_tools.local.yaml template, value already set', KEY)
            continue
        else:
            logger.info('Setting key [%s] in polarion_tools.local.yaml template', KEY)
            input_yaml[KEY] = replacement

    with open(output, 'w') as output_file:
        ruamel.yaml.round_trip_dump(input_yaml,
                                    output_file,
                                    indent=indent,
                                    block_seq_indent=block_indent)
    return 0


if __name__ == "__main__":
    main()
