import re
from collections.abc import Sequence

from bugzilla import Bugzilla as _Bugzilla
from cached_property import cached_property
from miq_version import LATEST
from miq_version import Version
from yaycl import AttrDict

from cfme.utils.conf import credentials
from cfme.utils.conf import env
from cfme.utils.log import logger
from cfme.utils.version import current_version

NONE_FIELDS = {"---", "undefined", "unspecified"}


class Product:
    def __init__(self, data):
        self._data = data

    @property
    def default_release(self):
        return Version(self._data["default_release"])

    @property
    def name(self):
        return self._data["name"]

    @property
    def milestones(self):
        return [ms["name"] for ms in self._data["milestones"]]

    @property
    def releases(self):
        return [release["name"] for release in self._data["releases"]]

    @property
    def versions(self):
        return sorted(
            Version(version["name"])
            for version in self._data["versions"]
            if version["name"] not in NONE_FIELDS
        )

    @property
    def latest_version(self):
        return self.versions[-1]


class Bugzilla:
    def __init__(self, **kwargs):
        # __kwargs passed to _Bugzilla instantiation, pop our args out
        self.__product = kwargs.pop("product", None)
        self.__config_options = kwargs.pop('config_options', {})
        self.__kwargs = kwargs
        self.__bug_cache = {}
        self.__product_cache = {}
        self.user = kwargs.get('user')
        self.password = kwargs.get('password')
        self.key = kwargs.get('api_key')

    @property
    def bug_count(self):
        return len(self.__bug_cache)

    @property
    def bugs(self):
        yield from self.__bug_cache.values()

    def products(self, *names):
        return [Product(p) for p in self.bugzilla._proxy.Product.get({"names": names})["products"]]

    def product(self, product):
        if product not in self.__product_cache:
            self.__product_cache[product] = self.products(product)[0]
        return self.__product_cache[product]

    @property
    def default_product(self):
        return None if self.__product is None else self.product(self.__product)

    @classmethod
    def from_config(cls):
        bz_conf = env.get('bugzilla', {})  # default empty so we can call .get() later
        url = bz_conf.get('url')
        if url is None:
            url = 'https://bugzilla.redhat.com/xmlrpc.cgi'
            logger.warning("No Bugzilla URL specified in conf, using default: %s", url)
        cred_key = bz_conf.get("credentials")
        bz_kwargs = dict(
            url=url,
            cookiefile=None,
            tokenfile=None,
            product=bz_conf.get("bugzilla", {}).get("product"),
            config_options=bz_conf)
        if cred_key:
            bz_creds = credentials.get(cred_key, {})
            if bz_creds.get('username'):
                logger.info('Using username/password for Bugzilla authentication')
                bz_kwargs.update(dict(
                    user=bz_creds.get("username"),
                    password=bz_creds.get("password")
                ))
            elif bz_creds.get('api_key'):
                logger.info('Using api key for Bugzilla authentication')
                bz_kwargs.update(dict(api_key=bz_creds.get('api_key')))
            else:
                logger.error('Credentials key for bugzilla does not have username or api key')
        else:
            logger.warn('No credentials found for bugzilla')

        return cls(**bz_kwargs)

    @cached_property
    def bugzilla(self):
        return _Bugzilla(**self.__kwargs)

    @cached_property
    def loose(self):
        return self.__config_options.get("loose", [])

    @cached_property
    def open_states(self):
        return set(self.__config_options.get("skip", []))

    @cached_property
    def upstream_version(self):
        if self.default_product is not None:
            return self.default_product.latest_version
        else:
            return Version(self.__config_options.get("upstream_version", Version.latest().vstring))

    def get_bug(self, id):
        id = int(id)
        if id not in self.__bug_cache:
            self.__bug_cache[id] = BugWrapper(self, self.bugzilla.getbug(id))
        return self.__bug_cache[id]

    def get_bug_variants(self, id):
        if isinstance(id, BugWrapper):
            bug = id
        else:
            bug = self.get_bug(id)
        expanded = set()
        found = set()
        stack = {bug}
        while stack:
            b = stack.pop()
            if b.status == "CLOSED" and b.resolution == "DUPLICATE":
                b = self.get_bug(b.dupe_of)
            found.add(b)
            if b.copy_of:
                stack.add(self.get_bug(b.copy_of))
            if b not in expanded:
                for cp in map(self.get_bug, b.copies):
                    found.add(cp)
                    stack.add(cp)
                expanded.add(b)
        return found

    def resolve_blocker(self, blocker, version=None, ignore_bugs=None, force_block_streams=None):
        # ignore_bugs is mutable but is not mutated here! Same force_block_streams
        force_block_streams = force_block_streams or []
        ignore_bugs = set() if not ignore_bugs else ignore_bugs
        if isinstance(id, BugWrapper):
            bug = blocker
        else:
            bug = self.get_bug(blocker)
        if version is None:
            version = current_version()
        if version == LATEST:
            version = bug.product.latest_version
        is_upstream = version == bug.product.latest_version
        variants = self.get_bug_variants(bug)
        filtered = set()
        version_series = ".".join(str(version).split(".")[:2])
        for variant in sorted(variants, key=lambda variant: variant.id):
            if variant.id in ignore_bugs:
                continue
            if variant.version is not None and variant.version > version:
                continue
            if variant.release_flag is not None and version.is_in_series(variant.release_flag):
                logger.info('Found matching bug for %d by release - #%d', bug.id, variant.id)
                filtered.clear()
                filtered.add(variant)
                break
            elif is_upstream and variant.release_flag == 'future':
                # It is an upstream bug
                logger.info('Found a matching upstream bug #%d for bug #%d', variant.id, bug.id)
                return variant
            elif (isinstance(variant.version, Version) and
                  isinstance(variant.target_release, Version) and
                  (variant.version.is_in_series(version_series) or
                   variant.target_release.is_in_series(version_series))):
                filtered.add(variant)
            else:
                logger.warning(
                    "ATTENTION!!: No release flags, wrong versions, ignoring %s", variant.id)
        if not filtered:
            # No appropriate bug was found
            for forced_stream in force_block_streams:
                # Find out if we force this bug.
                if version.is_in_series(forced_stream):
                    return bug
            else:
                # No bug, yipee :)
                return None
        # First, use versions
        for bug in filtered:
            if (isinstance(bug.version, Version) and
                isinstance(bug.target_release, Version) and
                not check_fixed_in(bug.fixed_in, version_series) and
                (bug.version.is_in_series(version_series) or
                 bug.target_release.is_in_series(version_series))):
                return bug
        # Otherwise prefer release_flag
        for bug in filtered:
            if bug.release_flag and version.is_in_series(bug.release_flag):
                return bug
        return None

    def set_flags(self, idlist, flags):
        # set the flags
        for bug in self.bugzilla.getbugs(idlist):
            result = bug.updateflags(flags)
            logger.info("Got %s from updating %s", result, bug)

    def get_bz_info(self, idlist, clones=True):
        """ Get information about the BZs in idlist """
        logger.info("Getting information about the following BZ's: %s", idlist)

        # build info
        info = {}
        for bug_id, bug in zip(idlist, self.bugzilla.getbugs(idlist)):
            # safety first
            if not bug:
                logger.error(f'BZ {bug_id} is None while processing bz info, '
                             'likely requires authentication, skipping')
                continue

            # assign some attrs for each BZ
            info[bug_id] = AttrDict(
                description=bug.description,
                summary=bug.summary,
                flags=bug.flags,
                qa_contact=bug.qa_contact,
                is_open=bug.is_open,
                status=bug.status,
                keywords=bug.keywords,
                blocks=bug.blocks,
            )
            variants = self.get_bug_variants(bug_id)
            if clones and variants:
                # add clones into the info list
                # variants are BugWrappers
                for clone in variants:
                    logger.info(f'Handling BZ clone for info: {clone._bug}')
                    info[clone._bug.id] = AttrDict(
                        description=clone._bug.description,
                        summary=clone._bug.summary,
                        flags=clone._bug.flags,
                        qa_contact=clone._bug.qa_contact,
                        is_open=clone._bug.is_open,
                        status=clone._bug.status,
                        keywords=clone._bug.keywords,
                        blocks=clone._bug.blocks,
                    )
        return info


def check_fixed_in(fixed_in, version_series):
    # used to check if the bug belongs to that series
    if fixed_in is None:
        return False
    if not isinstance(fixed_in, Version):
        fixed_in = Version(fixed_in)
    return fixed_in.is_in_series(version_series)


class BugWrapper:
    _copy_matchers = list(map(re.compile, [
        r'^[+]{3}\s*This bug is a CFME zstream clone. The original bug is:\s*[+]{3}\n[+]{3}\s*'
        r'https://bugzilla.redhat.com/show_bug.cgi\?id=(\d+)\.\s*[+]{3}',
        r"^\+\+\+ This bug was initially created as a clone of Bug #([0-9]+) \+\+\+"
    ]))

    def __init__(self, bugzilla, bug):
        self._bug = bug
        self._bugzilla = bugzilla

    @property
    def loose(self):
        return self._bugzilla.loose

    @property
    def bugzilla(self):
        return self._bugzilla

    def __getattr__(self, attr):
        """This proxies the attribute queries to the Bug object and modifies its result.

        If the field looked up is specified as loose field, it will be converted to Version.
        If the field is string and it has zero length, or the value is specified as "not specified",
        it will return None.
        """
        value = getattr(self._bug, attr)
        if attr in self.loose:
            if isinstance(value, Sequence) and not isinstance(value, str):
                value = value[0]
            value = value.strip()
            if not value:
                return None
            if value.lower() in NONE_FIELDS:
                return None
            # We have to strip any leading non-number characters to correctly match
            value = re.sub(r"^[^0-9]+", "", value)
            if not value:
                return None
            return Version(value)
        if isinstance(value, str):
            if len(value.strip()) == 0:
                return None
            else:
                return value
        else:
            return value

    @property
    def qa_whiteboard(self):
        """Returns a set of QA Whiteboard markers.

        It relies on the fact, that our QA Whiteboard uses format foo:bar:baz.

        Should be able to handle cases like 'foo::bar', or 'abc:'.
        """
        return {x.strip() for x in self._bug.qa_whiteboard.strip().split(":") if x.strip()}

    @property
    def copy_of(self):
        """Returns either id of the bug this is copy of, or None, if it is not a copy."""
        try:
            first_comment = self._bug.comments[0]["text"].lstrip()
        except IndexError:
            return None

        for copy_matcher in self._copy_matchers:
            copy_match = copy_matcher.match(first_comment)
            if copy_match is not None:
                return int(copy_match.groups()[0])
        else:
            return None

    @property
    def copies(self):
        """Returns list of copies of this bug."""
        result = []
        for bug_id in self._bug.blocks:
            bug = self._bugzilla.get_bug(bug_id)
            if bug.copy_of == self._bug.id:
                result.append(bug_id)
        return list(map(int, result))

    @property
    def _release_flag_data(self):
        for flag in self.flags:
            if flag["name"].startswith("cfme-"):
                release_flag = flag["name"].split("-", 1)[-1]
                if release_flag.endswith(".z"):
                    return release_flag.rsplit(".", 1)[0], True
                else:
                    return release_flag, False
        else:
            return None, False

    @property
    def release_flag(self):
        return self._release_flag_data[0]

    @property
    def zstream(self):
        return self._release_flag_data[1]

    @property
    def is_opened(self):
        states = self._bugzilla.open_states
        # we consider "POST" and "MODIFIED" to still be open states
        states.add('POST')
        states.add('MODIFIED')
        return self.status in states

    @property
    def product(self):
        return self._bugzilla.product(self._bug.product)

    @property
    def upstream_bug(self):
        if self.version is None:
            return True
        return self.version >= self.product.latest_version

    @property
    def can_test_on_upstream(self):
        change_states = {"POST", "MODIFIED"}
        return self.status in change_states

    def __repr__(self):
        return repr(self._bug)

    def __str__(self):
        return str(self._bug)
