# -*- coding: utf-8 -*-
from widgetastic.widget import View, Text

from cfme import BaseLoggedInPage
from widgetastic_patternfly import Dropdown
from widgetastic_manageiq import DetailsToolBarViewSelector
from widgetastic_manageiq import (BreadCrumb,
                                  SummaryTable,
                                  Button,
                                  TimelinesView)


class ProviderDetailsToolBar(View):
    """
    represents provider toolbar and its controls
    """
    monitoring = Dropdown(text='Monitoring')
    configuration = Dropdown(text='Configuration')
    reload = Button(title='Reload Current Display')
    policy = Dropdown(text='Policy')
    authentication = Dropdown(text='Authentication')

    @View.nested
    class view_selector(DetailsToolBarViewSelector):  # NOQA
        pass


class ProviderDetailsSummaryView(View):
    """
    represents Details page when it is switched to Summary aka Tables view
    """
    properties = SummaryTable(title="Properties")
    status = SummaryTable(title="Status")
    relationships = SummaryTable(title="Relationships")
    overview = SummaryTable(title="Overview")
    smart_management = SummaryTable(title="Smart Management")


class ProviderDetailsDashboardView(View):
    """
     represents Details page when it is switched to Dashboard aka Widgets view
    """
    # todo: need to develop this page
    pass


class ProviderDetailsView(BaseLoggedInPage):
    """
     main Details page
    """
    title = Text('//div[@id="main-content"]//h1')
    breadcrumb = BreadCrumb(locator='//ol[@class="breadcrumb"]')

    @View.nested
    class toolbar(ProviderDetailsToolBar):  # NOQA
        pass

    @View.nested
    class contents(View):  # NOQA
        pass

    def __getattribute__(self, item):
        # todo: to replace this code with switchable views asap
        if item == 'contents':
            if self.context['object'].appliance.current_version() >= '5.7':
                view_type = self.toolbar.view_selector.selected
                if view_type == 'Summary View':
                    return ProviderDetailsSummaryView(parent=self)

                elif view_type == 'Dashboard View':
                    return ProviderDetailsDashboardView(parent=self)

                else:
                    raise Exception('The form for provider with such name '
                                    'is absent: {}'.format(self.prov_type.text))
            else:
                return ProviderDetailsSummaryView(parent=self)  # 5.6 has only only Summary view

        else:
            return super(ProviderDetailsView, self).__getattribute__(item)

    @property
    def is_displayed(self):
        if self.context['object'].appliance.current_version() >= '5.7':
            subtitle = 'Summary' if self.toolbar.view_selector.selected == 'Summary View' \
                else 'Dashboard'
        else:
            subtitle = 'Summary'  # 5.6 has only only Summary view
        title = '{name} ({subtitle})'.format(name=self.context['object'].name, subtitle=subtitle)

        return self.logged_in_as_current_user and \
            self.navigation.currently_selected == ['Compute', 'Infrastructure', 'Providers'] and \
            self.breadcrumb.active_location == title


class ProviderTimelinesView(TimelinesView, BaseLoggedInPage):
    """
     represents Timelines page
    """
    @property
    def is_displayed(self):
        return self.logged_in_as_current_user and \
            self.navigation.currently_selected == ['Compute', 'Infrastructure', 'Providers'] \
            and TimelinesView.is_displayed
