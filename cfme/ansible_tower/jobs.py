import attr

from navmazing import NavigateToAttribute, NavigateToSibling
from widgetastic.widget import Text, View
from widgetastic_patternfly import Dropdown, Button
from widgetastic_manageiq import (Search, ItemsToolBarViewSelector, PaginationPane,
        BaseEntitiesView, SummaryTable)

from cfme.base.login import BaseLoggedInPage
from cfme.modeling.base import BaseEntity, BaseCollection
from cfme.utils.appliance.implementations.ui import navigator, CFMENavigateStep, navigate_to


class TowerJobsToolbar(View):
    configuration = Dropdown('Configuration')
    policy = Dropdown('Policy')
    download = Dropdown('Download')
    view_selector = View.nested(ItemsToolBarViewSelector)


class TowerJobsView(BaseLoggedInPage):
    search = View.nested(Search)
    toolbar = View.nested(TowerJobsToolbar)
    paginator = PaginationPane()
    including_entities = View.include(BaseEntitiesView, use_parent=True)

    @property
    def in_jobs(self):
        title = 'Ansible Tower Jobs'
        return (self.title.text == title and self.logged_in_as_current_user and
                self.navigation.currently_selected == ['Automation', 'Ansible Tower', 'Jobs'])


class TowerJobsDefaultView(TowerJobsView):
    title = Text("#explorer_title_text")

    @property
    def is_displayed(self):
        return (
            self.in_jobs and
            self.title.text == 'Ansible Tower Jobs'
        )


class AnsibleTowerJobsDetailsView(View):
    title = Text('//div[@id="main-content"]//h1')
    configuration = Dropdown('Configuration')
    policy = Dropdown('Policy')
    download = Button(title='Download')
    search = View.nested(Search)

    @View.nested
    class entities(View):  # noqa
        """ Represents details page when it's switched to Summary/Table view """
        properties = SummaryTable(title="Properties")
        relationships = SummaryTable(title="Relationships")
        smart_management = SummaryTable(title="Smart Management")

    @property
    def is_displayed(self):
        """Is this view being displayed?"""
        title = '{} (Summary)'.format(self.obj.name)
        return self.title.text == title


@attr.s
class TowerJobs(BaseEntity):
    # pass

    template_name = attr.ib()

    @property
    def status(self):
        view = navigate_to(self.parent, 'All')
        job_status = ''
        for row in view.entities.elements:
            print(row['Template Name'].read())
            if row['Template Name'].read() == self.template_name and job_status == '':
                job_status = row.status.text
            else:
                pass
        return job_status

    def delete(self):
        view = navigate_to(self.parent, 'All')
        view.configuration.item_select('Remove Jobs', handle_alert=True)


@attr.s
class TowerJobsCollection(BaseCollection):
    ENTITY = TowerJobs

    def all(self):
        # a.collections.ansible_tower_jobs.filter({"id":'1469'})
        id = self.filters.get('id', 0)
        teml_name = self.filters.get('temp_name')
        view = navigate_to(self, 'All')
        jobs = []
        # for row in view.items.rows():
        for _ in view.entities.paginator.pages():
            for row in view.entities.elements:
                if int(row.id.text) > int(id):
                    if teml_name == row.template_name.text:
                        jobs.append(self.instantiate(template_name=row.template_name.text))
        return jobs

    def first_by_date(self):
        view = navigate_to(self, 'All')
        # view.items.sort_by(column='Created On', order='asc')
        view.entities.elements.sort_by(column='Created On', order='asc')
        # row = view.items[0]
        row = view.entities.elements[0]
        job = self.instantiate(template_name=row.template_name.text)
        return job

    def is_all_finished(self):
        jobs = self.all()
        for job in jobs:
            if job.status == "successfull":
                return True
        return False

    def delete(self):
        # jobs = self.all()
        for job in self.all():
            job.delete()

    def delete_all(self):
        view = navigate_to(self, 'All')
        view.paginator.check_all()
        view.configuration.item_select('Remove Jobs', handle_alert=True)

    def is_finished(self):
        job = self.first_by_date()
        if job.status == "successful":
            return True
        else:
            return False


@navigator.register(TowerJobsCollection, 'All')
class All(CFMENavigateStep):
    VIEW = TowerJobsDefaultView
    prerequisite = NavigateToAttribute('appliance.server', 'LoggedIn')

    def step(self, *args, **kwargs):
        self.prerequisite_view.navigation.select('Automation', 'Ansible Tower', 'Jobs')

    def resetter(self):
        self.view.toolbar.view_selector.select('List View')


@navigator.register(TowerJobsCollection)
class Details(CFMENavigateStep):
    VIEW = AnsibleTowerJobsDetailsView
    prerequisite = NavigateToSibling('All')

    def step(self):
        # self.prerequisite_view.items.row(template_name=self.obj.name).click()
        self.prerequisite_view.entities.get_entity(name=self.obj.name).click()
# =======
# from navmazing import NavigateToSibling, NavigateToAttribute
# from widgetastic_patternfly import Button
# from widgetastic_manageiq import BaseEntitiesView
# from cfme.utils.appliance.implementations.ui import navigator, navigate_to
# from widgetastic_manageiq import ItemsToolBarViewSelector, SummaryTable


# class AnsibleTowerJobsView(View):
#    title = Text('//div[@id="main-content"]//h1')
    # configuration = Dropdown('Configuration')
    # policy = Dropdown('Policy')
    # download = Dropdown(title='Download')
    # items = Table('//div[@id="main_div"]//div[@id="list_grid" or @id="gtl_div"]//table')
    # view_selector = View.nested(ItemsToolBarViewSelector)
    # paginator = PaginationPane()
    # search = View.nested(Search)
    # including_entities = View.include(BaseEntitiesView, use_parent=True)

    # @property
    # def is_displayed(self):
    #     """Is this view being displayed?"""
    #     title = 'Ansible Tower Jobs'
    #     return (self.title.text == title and self.logged_in_as_current_user and
    #             self.navigation.currently_selected == ['Automation', 'Ansible Tower', 'Jobs'])

    # @View.nested
    # class toolbar(View): # noqa
    #    view_selector = View.nested(ItemsToolBarViewSelector)


# class AnsibleTowerJobsDetailsView(View):
#     title = Text('//div[@id="main-content"]//h1')
#     configuration = Dropdown('Configuration')
#     policy = Dropdown('Policy')
#     download = Button(title='Download')
#     search = View.nested(Search)
# 
#     @View.nested
#     class entities(View):  # noqa
#         """ Represents details page when it's switched to Summary/Table view """
#         properties = SummaryTable(title="Properties")
#         relationships = SummaryTable(title="Relationships")
#         smart_management = SummaryTable(title="Smart Management")
# 
#     @property
#     def is_displayed(self):
#         """Is this view being displayed?"""
#         title = '{} (Summary)'.format(self.obj.name)
#         return self.title.text == title


# @attr.s
# class AnsibleTowerJob(BaseEntity):
# 
#     template_name = attr.ib()
# 
#     @property
#     def status(self):
#         view = navigate_to(self.parent, 'All')
#         job_status = ''
#         for row in view.entities.elements:
#             print(row['Template Name'].read())
#             if row['Template Name'].read() == self.template_name and job_status == '':
#                 job_status = row.status.text
#             else:
#                 pass
#         return job_status
# 
#     def delete(self):
#         view = navigate_to(self.parent, 'All')
#         view.configuration.item_select('Remove Jobs', handle_alert=True)


# @attr.s
# class AnsibleTowerJobsCollection(BaseCollection):
#     ENTITY = AnsibleTowerJob
# 
#     def all(self):
#         # a.collections.ansible_tower_jobs.filter({"id":'1469'})
#         id = self.filters.get('id', 0)
#         teml_name = self.filters.get('temp_name')
#         view = navigate_to(self, 'All')
#         jobs = []
#         # for row in view.items.rows():
#         for _ in view.entities.paginator.pages():
#             for row in view.entities.elements:
#                 if int(row.id.text) > int(id):
#                     if teml_name == row.template_name.text:
#                         jobs.append(self.instantiate(template_name=row.template_name.text))
#         return jobs
# 
#     def first_by_date(self):
#         view = navigate_to(self, 'All')
#         # view.items.sort_by(column='Created On', order='asc')
#         view.entities.elements.sort_by(column='Created On', order='asc')
#         # row = view.items[0]
#         row = view.entities.elements[0]
#         job = self.instantiate(template_name=row.template_name.text)
#         return job
# 
#     def is_all_finished(self):
#         jobs = self.all()
#         for job in jobs:
#             if job.status == "successfull":
#                 return True
#         return False
# 
#     def delete(self):
#         # jobs = self.all()
#         for job in self.all():
#             job.delete()
# 
#     def delete_all(self):
#         view = navigate_to(self, 'All')
#         view.paginator.check_all()
#         view.configuration.item_select('Remove Jobs', handle_alert=True)
# 
#     def is_finished(self):
#         job = self.first_by_date()
#         if job.status == "successful":
#             return True
#         else:
#             return False


# @navigator.register(AnsibleTowerJobsCollection)
# class All(CFMENavigateStep):
#     VIEW = AnsibleTowerJobsView
#     prerequisite = NavigateToAttribute('appliance.server', 'LoggedIn')
# 
#     def step(self):
#         self.prerequisite_view.navigation.select('Automation', 'Ansible Tower', 'Jobs')
# 
#     def resetter(self):
#         self.view.toolbar.view_selector.select('List View')


# @navigator.register(AnsibleTowerJobsCollection)
# class Details(CFMENavigateStep):
#     VIEW = AnsibleTowerJobsDetailsView
#     prerequisite = NavigateToSibling('All')
# 
#     def step(self):
#         # self.prerequisite_view.items.row(template_name=self.obj.name).click()
#         self.prerequisite_view.entities.get_entity(name=self.obj.name).click()
# >>>>>>> first pr commit
