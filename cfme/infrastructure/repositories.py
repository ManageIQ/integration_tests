"""Infrastructure / Repositories"""

from functools import partial

import cfme.fixtures.pytest_selenium as sel
import cfme.web_ui.flash as flash
from cfme.web_ui import menu
import cfme.web_ui.toolbar as tb


from cfme.web_ui import Region, Form, Input, fill, form_buttons, Quadicon
from cfme.web_ui.form_buttons import FormButton
from cfme.web_ui.paginator import pages
from cfme.web_ui.tables import Table, Split
from utils.update import Updateable
from utils.pretty import Pretty
from utils.version import LOWEST, current_version

repo_list = Table.create(
    Split(
        "//div[@id='list_grid']/div[1]//tbody",
        "//div[@id='list_grid']/div[2]//tbody",
        1, 1),
    {'checkbox'},
    {'header_checkbox_locator': '#masterToggle'})

details_page = Region(infoblock_type='detail')

form = Form(
    fields=[
        ('name', Input('repo_name')),
        ('path', Input('repo_path')),
    ]
)

add_btn = {
    LOWEST: FormButton('Add this Repository'),
    # wonky upstream locator
    '5.4': '//button[.="Add"]'
}
save_btn = {
    LOWEST: form_buttons.save,
    '5.4': '//button[.="Save"]'
}
cfg_btn = partial(tb.select, 'Configuration')
pol_btn = partial(tb.select, 'Policy')


def _repo_row(name):
    for page in pages():
        row = repo_list.find_row('Name', name)
        if row:
            return row
    else:
        raise Exception('row not found for repo {}'.format(name))


def _repo_nav_fn(context):
    repo = context['repository']
    if current_version() >= '5.4':
        quadicon = Quadicon(repo.name, "repository")
        sel.click(quadicon.locate())
    else:
        sel.click(_repo_row(repo.name)[1])
    sel.wait_for_element(repo._detail_page_identifying_loc)


def _check_repo(name, callback=None):
    if current_version() >= '5.4':
        quadicon = Quadicon(name, "repository")
        sel.check(quadicon.checkbox())
    else:
        sel.check(sel.element('.//img', root=_repo_row(name)[0]))
    if callback:
        return callback()


menu.nav.add_branch(
    'infrastructure_repositories', {
        'infrastructure_repository_new': lambda _: cfg_btn('Add a new Repository'),
        'infrastructure_repository_edit': lambda ctx: _check_repo(ctx['repository'].name,
            lambda: cfg_btn('Edit the Selected Repository')),
        'infrastructure_repository': [
            _repo_nav_fn, {
                'infrastructure_repository_policy_assignment': lambda _: pol_btn('Manage Policies'),
                'infrastructure_repository_policy_tags': lambda _: pol_btn('Edit Tags'),
            }
        ]
    }
)


class Repository(Updateable, Pretty):
    """
    Model of an infrastructure repository in cfme.

    Args:
        name: Name of the repository host
        path: UNC path to the repository share

    Usage:

        myrepo = Repository(name='vmware', path='//hostname/path/to/share')
        myrepo.create()

    """
    pretty_attrs = ['name', 'path']

    def __init__(self, name=None, path=None):
        self.name = name
        self.path = path
        self._detail_page_identifying_loc = "//h1[contains(., '{}')]".format(self.name)

    def _submit(self, cancel, submit_button):
        if cancel:
            sel.click(form_buttons.cancel)
            # sel.wait_for_element(page.configuration_btn)
        else:
            sel.click(submit_button)
            flash.assert_no_errors()

    def create(self, cancel=False, validate_credentials=False):
        """
        Creates a repository in the UI

        Args:
           cancel (boolean): Whether to cancel out of the creation.  The cancel is done
               after all the information present in the Host has been filled in the UI.
           validate_credentials (boolean): Whether to validate credentials - if True and the
               credentials are invalid, an error will be raised.
        """
        sel.force_navigate('infrastructure_repository_new')
        fill(form, vars(self))
        self._submit(cancel, add_btn)

    def update(self, updates, cancel=False, validate_credentials=False):
        """
        Updates a repository in the UI.  Better to use utils.update.update context
        manager than call this directly.

        Args:
           updates (dict): fields that are changing.
           cancel (boolean): whether to cancel out of the update.
        """
        sel.force_navigate('infrastructure_repository_edit', context={'repository': self})
        fill(form, updates)
        self._submit(cancel, save_btn)

    def delete(self, cancel=False):
        """
        Deletes a repository from CFME

        Args:
            cancel: Whether to cancel the deletion, defaults to False
        """
        if self.exists:
            sel.force_navigate('infrastructure_repository', context={'repository': self})
            cfg_btn('Remove from the VMDB', invokes_alert=True)
            sel.handle_alert(cancel=cancel)

    def get_detail(self, *ident):
        """ Gets details from the details infoblock

        The function first ensures that we are on the detail page for the specific repository.

        Args:
            *ident: An InfoBlock title, followed by the Key name, e.g. "Relationships", "Images"
        Returns: A string representing the contents of the InfoBlock's value.
        """
        if not self._on_detail_page():
            sel.force_navigate('infrastructure_repository', context={'repository': self})
        return details_page.infoblock.text(*ident)

    def _on_detail_page(self):
        """ Returns ``True`` if on the repository detail page, ``False`` if not."""
        return self.is_displayed(self._detail_page_identifying_loc)

    @property
    def exists(self):
        sel.force_navigate('infrastructure_repositories')
        try:
            if current_version() >= '5.4':
                quadicon = Quadicon(self.name, "repository")
                return sel.is_displayed(quadicon.locate())
            else:
                return bool(_repo_row(self.name))
        except:  # exception?
            return False
