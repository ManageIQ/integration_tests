from navmazing import NavigateToAttribute, NavigateToSibling
from widgetastic_patternfly import Input, BootstrapSelect, Button, BootstrapSwitch
# TODO replace with dynamic table
from widgetastic_manageiq import VanillaTable

from cfme.base.ui import RegionView
from utils.appliance import Navigatable
from utils.appliance.implementations.ui import navigator, CFMENavigateStep, navigate_to
from utils.pretty import Pretty
from utils.update import Updateable


# =====================================CATEGORY===================================


class CompanyCategoriesAllView(RegionView):
    """Company Categories List View"""
    add_button = Button('Add')
    table = VanillaTable('//div[@id="settings_co_categories"]/table')

    @property
    def is_displayed(self):
        return (
            self.companycategories.is_active() and
            self.table.is_displayed
        )


class CompanyCategoriesAddView(CompanyCategoriesAllView):
    """ Add Company Categories View"""
    name = Input(id='name')
    display_name = Input(id='description')
    long_description = Input(id='example_text')
    show_in_console = BootstrapSwitch(id='show')
    single_value = BootstrapSwitch(id='single_value')
    capture_candu = BootstrapSwitch(id='perf_by_tag')

    cancel_button = Button('Cancel')

    @property
    def is_displayed(self):
        return (
            self.companycategories.is_active() and
            self.name.is_displayed
        )


class CompanyCategoriesEditView(CompanyCategoriesAddView):
    """Edit Company Categories View"""
    save_button = Button('Save')
    reset_button = Button('Reset')

    @property
    def is_displayed(self):
        return (
            self.companycategories.is_active() and
            self.name.is_displayed and
            self.save_button.is_displayed
        )


class Category(Pretty, Navigatable, Updateable):
    """ Class represents a category in CFME UI
        Args:
            name: Name of the category
            display_name: Category display name
            description: Category description
            show_in_console: Option to show category in console (True/False)
            single_value: Option if category is single value (True/False)
            capture_candu: True/False, capture c&u data by tag

    """
    pretty_attrs = ['name', 'display_name', 'description', 'show_in_console',
                    'single_value', 'capture_candu']

    def __init__(self, name=None, display_name=None, description=None, show_in_console=True,
                 single_value=True, capture_candu=False, appliance=None):
        Navigatable.__init__(self, appliance=appliance)
        self.name = name
        self.display_name = display_name
        self.description = description
        self.show_in_console = show_in_console
        self.single_value = single_value
        self.capture_candu = capture_candu

    def _form_mapping(self, **kwargs):
        """Returns dist used to fill forms """
        return {
            'name': kwargs.get('name'),
            'display_name': kwargs.get('display_name'),
            'long_description': kwargs.get('description'),
            'show_in_console': kwargs.get('show_in_console'),
            'single_value': kwargs.get('single_value'),
            'capture_candu': kwargs.get('capture_candu'),
        }

    def create(self, cancel=False):
        """ Create category method
            Args:
                cancel: To cancel creation pass True, cancellation message will be verified
                        By defaul user will be created
        """
        view = navigate_to(self, 'Add')
        view.fill(self._form_mapping(**self.__dict__))

        if cancel:
            view.cancel_button.click()
            flash_message = 'Add of new Category was cancelled by the user'
        else:
            view.add_button.click()
            flash_message = 'Category "{}" was added'.format(self.display_name)

        view = self.create_view(CompanyCategoriesAllView)
        view.flash.assert_success_message(flash_message)

    def update(self, updates, cancel=False):
        """ Update category method
            Args:
                updates: category data that should be changed
        """
        view = navigate_to(self, 'Edit')
        view.fill(self._form_mapping(**updates))
        if cancel:
            view.cancel_button.click()
            flash_message = 'Edit of Category "{}" was cancelled by the user'.format(self.name)
        else:
            view.save_button.click()
            flash_message = 'Category "{}" was saved'.format(self.name)

        view = self.create_view(CompanyCategoriesAllView)
        view.flash.assert_success_message(flash_message)

    def delete(self, cancel=True):
        """ Delete existing category
            Args:
                cancel: Default value 'True', category will be deleted
                        'False' - deletion of category will be canceled
        """
        view = navigate_to(self, 'All')
        row = view.table.row(name=self.name)
        row.actions.click()
        view.browser.handle_alert(cancel=cancel)
        if not cancel:
            view.flash.assert_success_message('Category "{}": Delete successful'.format(self.name))


@navigator.register(Category, 'All')
class CategoryAll(CFMENavigateStep):
    VIEW = CompanyCategoriesAllView
    prerequisite = NavigateToAttribute('appliance.server.zone.region', 'Details')

    def step(self):
        self.prerequisite_view.companycategories.select()


@navigator.register(Category, 'Add')
class CategoryAdd(CFMENavigateStep):
    VIEW = CompanyCategoriesAddView
    prerequisite = NavigateToSibling('All')

    def step(self):
        self.prerequisite_view.add_button.click()


@navigator.register(Category, 'Edit')
class CategoryEdit(CFMENavigateStep):
    VIEW = CompanyCategoriesEditView
    prerequisite = NavigateToSibling('All')

    def step(self):
        self.prerequisite_view.table.row(name=self.obj.name).click()

# =======================================TAGS=============================================


class CompanyTagsAllView(RegionView):
    """Company Tags list view"""
    category_dropdown = BootstrapSelect('classification_name')
    table = VanillaTable('//div[@id="classification_entries_div"]/table')
    add_button = Button('Add')

    cancel_button = Button('Cancel')

    @property
    def is_displayed(self):
        return (
            self.companycategories.is_active() and
            self.table.is_displayed
        )


class CompanyTagsAddView(CompanyTagsAllView):
    """Add Company Tags view"""
    tag_name = Input(id='entry_name')
    tag_description = Input(id='entry_description')

    @property
    def is_displayed(self):
        return (
            self.companycategories.is_active() and
            self.tag_name.is_displayed
        )


class CompanyTagsEditView(CompanyTagsAddView):
    """Edit Company Tags view"""
    save_button = Button('Save')
    reset_button = Button('Reset')


class Tag(Pretty, Navigatable, Updateable):
    """ Class represents a category in CFME UI
        Args:
            name: Name of the tag
            display_name: Tag display name
            category: Tags Category

    """
    pretty_attrs = ['name', 'display_name', 'category']

    def __init__(self, name=None, display_name=None, category=None, appliance=None):
        Navigatable.__init__(self, appliance=appliance)
        self.name = name
        self.display_name = display_name
        self.category = category

    def _form_mapping(self, **kwargs):
        """Returns dist used to fill forms """
        return {
            'tag_name': kwargs.get('name'),
            'tag_description': kwargs.get('display_name')
        }

    def create(self):
        """ Create category method """
        view = navigate_to(self, 'Add')
        view.fill(self._form_mapping(**self.__dict__))
        view.add_button.click()

    def update(self, updates):
        """ Update category method """
        view = navigate_to(self, 'Edit')
        view.fill(self._form_mapping(**updates))
        view.save_button.click()

    def delete(self, cancel=True):
        """ Delete category method """
        view = navigate_to(self, 'All')
        row = view.table.row(name=self.name)
        row.actions.click()
        view.browser.handle_alert(cancel=cancel)


@navigator.register(Tag, 'All')
class TagsAll(CFMENavigateStep):
    VIEW = CompanyTagsAllView
    prerequisite = NavigateToAttribute('appliance.server.zone.region', 'Details')

    def step(self):
        self.prerequisite_view.companytags.select()
        self.view.fill({'category_dropdown': self.obj.category.display_name})


@navigator.register(Tag, 'Add')
class TagsAdd(CFMENavigateStep):
    VIEW = CompanyTagsAddView
    prerequisite = NavigateToSibling('All')

    def step(self):
        self.prerequisite_view.add_button.click()


@navigator.register(Tag, 'Edit')
class TagsEdit(CFMENavigateStep):
    VIEW = CompanyTagsEditView
    prerequisite = NavigateToSibling('All')

    def step(self):
        self.prerequisite_view.table.row(name=self.obj.name).click()

# =======================================MAP TAGS==============================================


class MapTagsAllView(RegionView):
    """Map Tags list view"""
    table = VanillaTable('//div[@id="settings_label_tag_mapping"]/table')
    add_button = Button('Add')

    @property
    def is_displayed(self):
        return (
            self.maptags.is_active() and
            self.table.is_displayed
        )


class MapTagsAddView(RegionView):
    """Add Map Tags view"""
    resource_entity = BootstrapSelect(id='entity')
    resource_label = Input(id='label_name')
    category = Input(id='category')

    add_button = Button('Add')
    cancel_button = Button('Cancel')

    @property
    def is_displayed(self):
        return (
            self.maptags.is_active() and
            self.resource_entity.is_displayed
        )


class MapTagsEditView(MapTagsAddView):
    """Edit Map Tags view"""
    save_button = Button('Save')
    reset_button = Button('Reset')


class MapTags(Navigatable, Pretty, Updateable):
    """ Class represents a category in CFME UI
        Args:
            entity: Name of the tag
            label: Tag display name
            category: Tags Category

    """
    pretty_attrs = ['entity', 'label', 'category']

    def __init__(self, entity=None, label=None, category=None, appliance=None):
        Navigatable.__init__(self, appliance=appliance)
        self.entity = entity
        self.label = label
        self.category = category

    def _form_mapping(self, **kwargs):
        """Returns dist used to fill forms """
        return {
            'resource_entity': kwargs.get('entity'),
            'resource_label': kwargs.get('label'),
            'category': kwargs.get('category')
        }

    def create(self, cancel=False):
        """ Map tags creation method
            Args:
                cancel: True - if you want to cancel map creation,
                        by defaul map will be created
        """
        view = navigate_to(self, 'Add')
        view.fill(self._form_mapping(**self.__dict__))

        if cancel:
            view.cancel_button.click()
            flash_message = 'Add of new Container Label Tag Mapping was cancelled by the user'
        else:
            view.add_button.click()
            flash_message = 'Container Label Tag Mapping "{}" was added'.format(self.label)

        view = self.create_view(MapTagsAllView)
        view.flash.assert_success_message(flash_message)

    def update(self, updates, cancel=False):
        """ Update tag map method
            Args:
                updates: tag map data that should be changed
                cancel: True - if you want to cancel map edition,
                        by defaul map will be updated
        """
        view = navigate_to(self, 'Edit')
        # only category can be updated, as other fields disabled by default
        view.fill({
            'category': updates.get('category')
        })

        if cancel:
            view.cancel_button.click()
            flash_message = (
                'Edit of Container Label Tag Mapping "{}" was cancelled by the user'.format(
                    self.label)
            )
        else:
            view.save_button.click()
            flash_message = 'Container Label Tag Mapping "{}" was saved'.format(self.label)

        view = self.create_view(MapTagsAllView, override=updates)
        view.flash.assert_success_message(flash_message)

    def delete(self, cancel=False):
        """ Delete existing user
            Args:
                cancel: Default value 'False', map will be deleted
                        'True' - map will not be deleted
        """
        view = navigate_to(self, 'All')
        row = view.table.row(tag_category=self.category)
        row.actions.click()
        view.browser.handle_alert(cancel=cancel)

        if not cancel:
            view = self.create_view(MapTagsAllView)
            view.flash.assert_success_message(
                'Container Label Tag Mapping "{}": Delete successful'.format(self.label))


@navigator.register(MapTags, 'All')
class MapTagsAll(CFMENavigateStep):
    VIEW = MapTagsAllView
    prerequisite = NavigateToAttribute('appliance.server.zone.region', 'Details')

    def step(self):
        self.prerequisite_view.maptags.select()


@navigator.register(MapTags, 'Add')
class MapTagsAdd(CFMENavigateStep):
    VIEW = MapTagsAddView
    prerequisite = NavigateToSibling('All')

    def step(self):
        self.prerequisite_view.add_button.click()


@navigator.register(MapTags, 'Edit')
class MapTagsEdit(CFMENavigateStep):
    VIEW = MapTagsEditView
    prerequisite = NavigateToSibling('All')

    def step(self):
        self.prerequisite_view.table.row(tag_category=self.obj.category).click()
