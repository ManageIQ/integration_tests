from widgetastic.widget import Image
from widgetastic.widget import Text
from widgetastic.widget import View


class LinksView(View):
    """
    Widgets for all of the links on the documentation page
    Each doc link is an anchor with a child image element, then an anchor with text
    Both the image and the text anchor should link to the same PDF
    """
    # todo: update this view. it contains too much duplicate code
    @View.nested
    class policies(View):  # noqa
        TEXT = 'Defining Policies Profiles Guide'
        link = img_anchor = Text('//a[@title="View the {}"]'.format(TEXT))
        img = Image(locator='//img[@alt="View the {}"]'.format(TEXT))

    @View.nested
    class general(View):  # noqa
        TEXT = 'General Configuration Guide'
        link = img_anchor = Text('//a[@title="View the {}"]'.format(TEXT))
        img = Image(locator='//img[@alt="View the {}"]'.format(TEXT))

    @View.nested
    class inventory(View):  # noqa
        TEXT = 'Infrastructure Inventory Guide'
        link = img_anchor = Text('//a[@title="View the {}"]'.format(TEXT))
        img = Image(locator='//img[@alt="View the {}"]'.format(TEXT))

    @View.nested
    class automation(View):  # noqa
        TEXT = 'Methods For Automation Guide'
        link = img_anchor = Text('//a[@title="View the {}"]'.format(TEXT))
        img = Image(locator='//img[@alt="View the {}"]'.format(TEXT))

    @View.nested
    class monitoring(View):  # noqa
        TEXT = 'Monitoring Alerts Reporting Guide'
        link = img_anchor = Text('//a[@title="View the {}"]'.format(TEXT))
        img = Image(locator='//img[@alt="View the {}"]'.format(TEXT))

    @View.nested
    class providers(View):  # noqa
        TEXT = 'Providers Guide'
        link = img_anchor = Text('//a[@title="View the {}"]'.format(TEXT))
        img = Image(locator='//img[@alt="View the {}"]'.format(TEXT))

    @View.nested
    class rest(View):  # noqa
        TEXT = 'Rest Api Guide'
        link = img_anchor = Text('//a[@title="View the {}"]'.format(TEXT))
        img = Image(locator='//img[@alt="View the {}"]'.format(TEXT))

    @View.nested
    class scripting(View):  # noqa
        TEXT = 'Scripting Actions Guide'
        link = img_anchor = Text('//a[@title="View the {}"]'.format(TEXT))
        img = Image(locator='//img[@alt="View the {}"]'.format(TEXT))

    @View.nested
    class vm_instances(View):  # noqa
        # TODO: title must be changed once BZ 1723813 is resolved.
        TEXT = 'Virtual Machines Hosts Guide'
        link = img_anchor = Text('//a[@title="View the {}"]'.format(TEXT))
        img = Image(locator='//img[@alt="View the {}"]'.format(TEXT))

    @View.nested
    class customer_portal(View):  # noqa
        TEXT = 'Red Hat Customer Portal'
        link = Text('//a[normalize-space(.)="{}"]'.format(TEXT))


class DocView(View):
    """
    View for the documentation page, a title and a bunch of pdf of links
    """
    @property
    def is_displayed(self):
        return (
            self.title.read() == 'Documentation' and
            all([link.is_displayed for link in self.links.sub_widgets])
        )

    title = Text('//div[@id="main-content"]//div/h1')
    links = View.nested(LinksView)
