from utils.log import logger

"""A simplified navigation framework with prerequisite, object and intelligence support.

An example is below::

    from utils.navigate import navigate, NavigateStep, NavigateToSibling

    class Provider(object):
        def __init__(self, name):
            self.name = name


    @navigate.register(Provider, 'New')
    class AddANewProvider(NavigateStep)
        prerequisite = NavigateToSibling('All')

        def step(self):
            click('Add New Button')

    @navigate.register(Provider, 'All')
    class ShowAllProviders(NavigateStep)
        def am_i_here(self):
            return check_if_i_am_already_on_page()

        def step(self):
            click('All button')

"""


class NavigationException(Exception):
    """Simple Exception when navigations can't be found"""
    def __init__(self, name, cls):
        self.name = name
        self.cls = cls

    def __str__(self):
        return "Couldn't find the destination [{}] with the given class [{}]".format(
            self.name, self.cls)


class Navigate(object):
    def __init__(self):
        """Initializes the destination dictionary for the Navigate object """
        self.dest_dict = {}

    def register(self, cls, name=None):
        """Decorator that registers a class with an optional name"""
        def f(obj):
            """This is part of the decorator class

            This function is returned and run with the class it decorates as the obj argument.
            The destination name is either the supplied name, or the class name of the NavigateStep
            object.
            """
            destination_name = name or obj.__name__
            obj._name = destination_name
            self.dest_dict[cls, destination_name] = obj
        return f

    def navigate(self, cls_or_obj, name):
        """This function performs the navigation

        We first determine if we have a class of an instance and find the class
        either way. We then walk the MRO for the class and attempt to find a matching
        destination name in the dest_dict. KeyErrors are expected and accepted. This
        allows us to override a destination in a subclass if we so desire, as the MRO
        walk means we will always go to the overridden version first.

        In any case, we instantiate the NavigateStep object there and then with the
        information we have been given, namely the object that we are using as context
        and this Navigate object. We next try to run the .go() method of the NavigateStep object

        If we exhaust the MRO and we have still not found a match, we raise an exception.
        """
        cls = type(cls_or_obj) if not isinstance(cls_or_obj, type) else cls_or_obj
        for _class in cls.__mro__:
            try:
                self.dest_dict[_class, name](cls_or_obj, self).go()
                break
            except KeyError:
                continue
        else:
            raise NavigationException(name, cls.__name__)


class NavigateToSibling(object):
    """This is a helper descriptor for navigation destinations which are linked to the same class.

    For instance, imagine you have an object that has a 'ViewAll', destination that needs to
    be visited before you can click on 'New'. In this instance, you would need to make the
    'New' destination use 'ViewAll' as a prerequisite. As this would need no other special
    input, we can use NavigateToSibling as a helper. This will set prerequisite to be a
    callable that will navigate to the prerequisite step.
    """
    def __init__(self, target, obj=None):
        self.target = target
        self.obj = obj

    def __get__(self, obj, owner):
        if self.obj is None:
            return type(self)(self.target, obj or owner)
        else:
            return self

    def __call__(self):
        self.obj.navigate_obj.navigate(self.obj.obj, self.target)


class NavigateStep(object):
    """A Navigation Step object

    The NavigateStep object runs through several key stages
    1) It checks to see if we are already at that navigation step, if so, we return
    2) It runs the prerequisite to see if there is a step that is required to be run
       before this one.
    3) It runs the step function to navigate to the current step after the prerequisite has been
       completed
    """
    def __init__(self, obj, navigate_obj):
        self.obj = obj
        self.navigate_obj = navigate_obj

    def am_i_here(self):
        return False

    def prerequisite(self):
        pass

    def step(self):
        return

    def go(self):
        logger.debug("NAVIGATE: Checking if already at {}".format(self._name))
        try:
            if self.am_i_here():
                return
        except Exception as e:
            logger.debug("NAVIGATE: Exception raised [{}] whilst checking if already at {}".format(
                e, self._name))
        self.prerequisite()
        logger.debug("NAVIGATE: Heading to destination {}".format(self._name))
        self.step()

navigate = Navigate()
