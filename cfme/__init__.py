from utils.update import Updateable
from utils.pretty import Pretty
from utils import version

from widgetastic.widget import View
from widgetastic_patternfly import NavDropdown, VerticalNavigation, FlashMessages


class Credential(Pretty):
    """
    A class to fill in credentials

    Args:
        principal: Something
        secret: Something
        verify_secret: Something
    """
    pretty_attrs = ['principal', 'secret']

    def __init__(self, principal=None, secret=None, verify_secret=None, **ignore):
        self.principal = principal
        self.secret = secret
        self.verify_secret = verify_secret

    def __getattribute__(self, attr):
        if attr == 'verify_secret':
            vs = object.__getattribute__(self, 'verify_secret')
            if vs is None:
                return object.__getattribute__(self, 'secret')
            else:
                return vs
        elif attr == "verify_token":
            try:
                vs = object.__getattribute__(self, 'verify_token')
            except AttributeError:
                return object.__getattribute__(self, 'token')
        else:
            return object.__getattribute__(self, attr)


class ProvCredential(Credential, Updateable):
    """Provider credentials

       Args:
         type: One of [amqp, candu, ssh, token] (optional)
         domain: Domain for default credentials (optional)
    """
    from cfme.web_ui import FileInput, Input, Radio, form_buttons
    from cfme.web_ui.tabstrip import TabStripForm

    @property
    def form(self):
        fields = [
            ('token_secret_55', Input('bearer_token')),
            ('google_service_account', Input('service_account')),
        ]
        tab_fields = {
            ("Default", ('default_when_no_tabs', )): [
                ('default_principal', Input("default_userid")),
                ('default_secret', Input("default_password")),
                ('default_verify_secret', Input("default_verify")),
                ('token_secret', {
                    version.LOWEST: Input('bearer_password'),
                    '5.6': Input('default_password')
                }),
                ('token_verify_secret', {
                    version.LOWEST: Input('bearer_verify'),
                    '5.6': Input('default_verify')
                }),
            ],

            "RSA key pair": [
                ('ssh_user', Input("ssh_keypair_userid")),
                ('ssh_key', FileInput("ssh_keypair_password")),
            ],

            "C & U Database": [
                ('candu_principal', Input("metrics_userid")),
                ('candu_secret', Input("metrics_password")),
                ('candu_verify_secret', Input("metrics_verify")),
            ],

            "Hawkular": [
                ('hawkular_validate_btn', form_buttons.validate),
            ]
        }
        fields_end = [
            ('validate_btn', form_buttons.validate),
        ]

        if version.current_version() >= '5.6':
            amevent = "Events"
        else:
            amevent = "AMQP"
        tab_fields[amevent] = []
        if version.current_version() >= "5.6":
            tab_fields[amevent].append(('event_selection', Radio('event_stream_selection')))
        tab_fields[amevent].extend([
            ('amqp_principal', Input("amqp_userid")),
            ('amqp_secret', Input("amqp_password")),
            ('amqp_verify_secret', Input("amqp_verify")),
        ])

        return TabStripForm(fields=fields, tab_fields=tab_fields, fields_end=fields_end)

    def __init__(self, **kwargs):
        super(ProvCredential, self).__init__(**kwargs)
        self.type = kwargs.get('cred_type', None)
        self.domain = kwargs.get('domain', None)
        if self.type == 'token':
            self.token = kwargs['token']
        if self.type == 'service_account':
            self.service_account = kwargs['service_account']


class BaseLoggedInPage(View):
    """This page should be subclassed by any page that models any other page that is available as
    logged in.
    """
    flash = FlashMessages('div#flash_text_div')
    help = NavDropdown('.//li[./a[@id="dropdownMenu1"]]')
    settings = NavDropdown('.//li[./a[@id="dropdownMenu2"]]')
    navigation = VerticalNavigation('#maintab')

    @property
    def is_displayed(self):
        return self.logged_in_as_current_user

    def logged_in_as_user(self, user):
        if self.logged_out:
            return False

        return user.name == self.current_fullname

    @property
    def logged_in_as_current_user(self):
        return self.logged_in_as_user(self.extra.appliance.user)

    @property
    def current_username(self):
        try:
            return self.extra.appliance.user.principal
        except AttributeError:
            return None

    @property
    def current_fullname(self):
        return self.settings.text.strip().split('|', 1)[0].strip()

    @property
    def logged_in(self):
        return self.settings.is_displayed

    @property
    def logged_out(self):
        return not self.logged_in

    def logout(self):
        self.settings.select_item('Logout')
        self.browser.handle_alert(wait=None)
        self.extra.appliance.user = None
