"""
Yet Another GitHub v3 Python wrapper and command-line tool

Assumptions:
    Python 2.7.x and 3.4+
    Linux, OS X
    Coding/naming conventions: Assumption: ~ PEP-8
    Queries apply to all public repositories in GitHub
    Output format of the "top-N repo" commands: newline-terminated repo names
    Output order: descending by given sort-stat value
    Output destination: stdout

"""

from __future__ import print_function

import logging
import numbers
import os
import sys
import time

PY2 = sys.version_info < (3,)
PY3 = not PY2

if PY3:
    from base64 import encodebytes as base64_encodebytes
    import configparser
else:
    from base64 import encodestring as base64_encodebytes  # pylint: disable=C0412
    import ConfigParser as configparser

import requests
import requests.adapters

_LOG = logging.getLogger('__name__')


class YagpyError(Exception):
    """Base yagpy error class"""
    pass


class RateLimitExceeded(YagpyError):
    """Raised with a helpful message when rate limit is exceeded"""
    pass


class ConfigLoadError(YagpyError):
    """Raised when we have a problem accessing the configuration file"""
    pass


class GitHubBasicAuthCredentials(object):
    """GitHub Basic Authentication credentials.

    TODO support other authentication methods, such as OAuth2
    """

    DEFAULT_CONFIG_PATH = '~/.yagpy/config'

    CONFIG_PATH_ENV_VAR = 'YAGPY_CONFIG_PATH'

    CONFIG_FILE_USER_VAR = 'github_user'
    CONFIG_FILE_PASSWORD_VAR = 'github_password'

    def __init__(self, user, password):
        """
        NOTE: user and password must both be either truthie or falsie. If
            truthie, both must be strings. If falsie, both must be empty
            strings. If empty strings, the API will make an attempt to
            load the authentication credentials from the configuration file
            referenced by the `YAGPY_CONFIG_PATH` environment variable,
            defaulting to `~/.yagpy/config`, in which case the values will be
            loaded from the `github_user` and `github_password` properties in
            the `[default]` section of the config file. If the config file is
            not found, prints a warning to stderr and defaults to
            unauthenticated access.

        TODO: support forced loading of credentials mode, e.g., with both set to
              True, that would raise if credentials aren't found.

        :param str user:
        :param str password:
        :raise ConfigLoadError: if error loading values from configuration
        """

        if bool(user) != bool(password):
            raise ValueError('user and password must be both either truthie or '
                             'falise, but got: user={!r}, password={!r}'
                             .format(user, password))

        self.user = user
        self.password = password

        if self.user == '':
            # (None, None) if authentication is bypassed
            self.user, self.password = self._load_from_config_file()

    def add_authentication_info(self, session):
        """Add authentication header to the given session object.

        :param requests.Session session:
        """
        if self.user is not None:
            session.auth = (self.user, self.password)

    @staticmethod
    def _encode_basic_auth(user, password):
        """base64-encode Basic Authentication header value

        :param str user:
        :param str password:
        :return: Basic Authentication header value
        :rtype: str
        """
        # NOTE: encodebytes adds a trailing newline that we don't want
        cred = base64_encodebytes(  # pylint: disable=W1505
            '{}:{}'.format(user, password).encode()).decode().rstrip('\n')

        return 'Basic {}'.format(cred)

    @classmethod
    def _load_from_config_file(cls):
        """

        :return: two-tuple (user, password); (None, None) if authentication
            is bypassed.
        :rtype: tuple
        :raises ConfigLoadError: if unexpected issue while attempting to load
            config file.
        """
        # Load configuration from our config file

        # First check if referenced via environment variable
        config_file_path = os.getenv(cls.CONFIG_PATH_ENV_VAR, None)
        if config_file_path is not None:
            if not os.path.isfile(config_file_path):
                raise ConfigLoadError(
                    'No config file found at location provided by environment '
                    'variable {}={!r}'.format(cls.CONFIG_PATH_ENV_VAR,
                                              config_file_path))
        else:
            config_file_path = os.path.expanduser(cls.DEFAULT_CONFIG_PATH)

        if not os.path.isfile(config_file_path):
            _LOG.debug('Authentication configuration file not found at %r',
                       config_file_path)
            print('WARNING: GitHub authentication configuration file not found '
                  'at {!r}, running in unauthenticated mode at reduced GitHub '
                  'request rate quota.'.format(config_file_path),
                  file=sys.stderr)
            # Bypass authentication
            return None, None

        try:
            config = configparser.ConfigParser()
            with open(config_file_path) as file:
                if PY3:
                    config.read_file(file)
                else:
                    config.readfp(file)  # pylint: disable=W1505

            user = config.get('default', cls.CONFIG_FILE_USER_VAR)
            password = config.get('default', cls.CONFIG_FILE_PASSWORD_VAR)
        except Exception as error:
            _LOG.debug('Error loading authentication configuration file %r.',
                       config_file_path, exc_info=True)
            raise ConfigLoadError(error)

        return user, password


class GitHub(object):
    """Root GitHub interface. Acts as container for general GitHub access
    attributes used by subordinate classes.

    TODO: authenticated users get a much larger request quota

    """
    BASE_API_URL = 'https://api.github.com'
    # API_URL_SCHEME = 'https://'
    # API_URL_HOST = 'api.github.com'

    V3_JSON_HEADER = {'Accept': 'application/vnd.github.v3+json'}

    HTTP_TIMEOUT = 30

    def __init__(self, credentials):
        """

        :param GitHubBasicAuthCredentials | None credentials: None to pypass
            GitHub authentication
        """
        self.cred = credentials
        if self.cred is not None and self.cred.user is None:
            self.cred = None

        # Use connection pooling and HTTP1.1 persistent connections
        self._http_session = requests.Session()

        # Override the default 0-retry limit
        self._http_session.mount(
            self.BASE_API_URL[:self.BASE_API_URL.index('//') + 2],
            requests.adapters.HTTPAdapter(max_retries=10))

        self._http_session.headers.update(self.V3_JSON_HEADER)

        if self.cred:
            self.cred.add_authentication_info(self._http_session)

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self._http_session.close()

    def org(self, name):
        """Provide access to the GitHub /orgs v3 API

        Usage example:
            # Get all source (non-fork) repos in the nodejs organization
            for item in GitHub().org('nodejs').repos().list_all_sources():
                print(item)

        :param str name: Name of the GitHub organization
        :return: GitHub organization interface
        :rtype: GitHubOrg
        """
        return GitHubOrg(self, name)

    def repo(self, owner, repo):
        """Provide access to the GitHub /repos v3 API

        Usage example:
            # Get all pull requests for a repo given its owner and name
            for item in GitHub().repo('nodejs', 'node').pulls().list_all():
                print(item)

        :param str owner: repo owner name
        :param str repo: repo name
        :return: GitHub repo interface
        :rtype: GitHubRepo
        """
        return GitHubRepo(self, owner, repo)

    def search(self):
        """Provide access to the GitHub /search v3 API.

        NOTE: this is for personal exploration, not part of assignment.

        Usage example:
            # Get the top-10 repos by number of stars in descending order
            for item in GitHub().search().repositories().by_stars().get(10):
                print(item)

        :return: GitHub search interface
        :rtype: GitHubSearch
        """
        return GitHubSearch(self)

    def paginate(self, base_url, base_query_args):
        """Helper utility for paginating GitHub GET requests that support the `page`
        query arg. Create a generator that yields all json-decoded pages starting
        with the first page.

        TODO Make more generic by using the Links header for paginating (not all
        GitHub v3 API methods use the `page` query arg for paginating)

        :param str base_url: base URL to which urlencoded query args will be
            appended.
        :param dict base_query_args: a dict of query args sans the `page` arg.
        :rtype: generator
        """
        if not base_url:
            raise ValueError(
                'Expected base_url string, but got {!r}.'.format(base_url))

        if 'page' in base_query_args:
            raise ValueError(
                'Unexpected "page" query arg in base_query_args: {!r}'.format(
                    base_query_args))

        next_page = 1  # 1-based
        while True:
            query = {'page': next_page}
            query.update(base_query_args)
            next_page += 1

            _LOG.debug(
                'Initiating HTTP request for page %s; URL: %r; query=%s and '
                'Headers: %r',
                next_page - 1,
                base_url,
                query,
                self._http_session.headers)

            try:
                response = self._http_session.get(base_url,
                                                  params=query,
                                                  timeout=self.HTTP_TIMEOUT)
                response.raise_for_status()
            except requests.exceptions.HTTPError as error:
                _LOG.debug('Error url=%r; headers=%s',
                           error.response.url,
                           error.response.headers,
                           exc_info=True)

                # 403 Forbidden; GitHub overloads it to signal rate limits too
                if error.response.status_code == 403:
                    info = error.response.headers

                    if ('X-RateLimit-Remaining' in info and
                            info['X-RateLimit-Remaining'] == '0'):
                        msg_parts = [
                            'TRANSIENT ERROR! GitHub API rate limit exhausted '
                            'while getting {!r}.'.format(error.response.url)]

                        if 'X-RateLimit-Limit' in info:
                            msg_parts.append(
                                'The rate limit is {} requests per hour.'.format(
                                    info['X-RateLimit-Limit']))

                        if 'X-RateLimit-Reset' in info:
                            reset_delta_min = ((int(info['X-RateLimit-Reset']) -
                                                time.time()) / 60)
                            reset_delta_min = round(max(0, reset_delta_min), 2)
                            msg_parts.append(
                                'Rate limit window resets in {} minutes.'.format(
                                    reset_delta_min))

                        raise RateLimitExceeded(' '.join(msg_parts))

                raise

            yield response.json()


class GitHubRepo(object):
    """GitHub /repos v3 interface"""

    BASE_PATH = '/repos'

    def __init__(self, hub, owner, repo):
        """
        :param GitHub hub: GitHub root interface.
        :param str owner: repo owner name
        :param str repo: repo name
        """
        if not owner:
            raise ValueError(
                'Expected repo owner name, but got {!r}'.format(owner))

        if not repo:
            raise ValueError(
                'Expected repo name, but got {!r}'.format(repo))

        self.hub = hub
        self.owner = owner
        self.name = repo

    def pulls(self):
        """Provide access to the GitHub /repos/:owner/:repo/pulls v3 API

        :rtype: GitHubRepo.RepoPulls
        """
        return self.RepoPulls(self)


    class RepoPulls(object):
        """GitHub /repos/:owner/:repo/pulls v3 API wrapper

        See https://developer.github.com/v3/pulls
        """

        def __init__(self, repo):
            """
            :param GitHubRepo repo:
            """
            self.repo = repo

        def list_all(self):
            """Crete a generator that yields ALL pull requests in the repo.
            Each yielded value is the decoded repo metadata dict from pages
            returned by `GET /repos/:owner/:repo/pulls?state=all`

            :rtype: generator
            """
            base_url = (self.repo.hub.BASE_API_URL +
                        self.repo.BASE_PATH +
                        '/' + self.repo.owner +
                        '/' + self.repo.name +
                        '/pulls')
            base_query = {'state': 'all', 'per_page': 100}

            total_items_rx = 0
            for page in self.repo.hub.paginate(base_url, base_query):
                num_items_rx = len(page)
                total_items_rx += num_items_rx
                _LOG.debug('Server returned %s items; running total=%s items',
                           num_items_rx, total_items_rx)

                if not num_items_rx:
                    _LOG.debug('Reached end of pull requests in repo %s/%s.',
                               self.repo.owner, self.repo.name)
                    break

                for item in page:
                    yield item


class GitHubOrg(object):
    """GitHub /orgs v3 interface"""

    BASE_PATH = '/orgs'

    def __init__(self, hub, name):
        """

        :param GitHub hub: GitHub root interface.
        :param str name: Name of the GitHub organization
        """
        if not name:
            raise ValueError('Expected org name, but got {!r}'.format(name))

        self.hub = hub
        self.name = name

    def repos(self):
        """Provide access to GitHub /orgs/:org/repos v3 API

        :rtype: GitHubOrg.OrgRepos
        """
        return self.OrgRepos(self)

    class OrgRepos(object):
        """GitHub /orgs/:org/repos v3 API wrapper

        See https://developer.github.com/v3/repos/
        """

        def __init__(self, org):
            """

            :param GitHubOrg org: GitHub org interface instance.
            """
            self.org = org

        def list_all_sources(self):
            """Create a generator that yields all of the organization's source
            (not forks) repos returned by `/orgs/:org/repos` as python dicts.

            GET /orgs/:orgname/repos?type=sources

            :rtype: generator
            """
            base_query = {'type': 'sources', 'per_page': 100}

            base_url = (self.org.hub.BASE_API_URL +
                        self.org.BASE_PATH +
                        '/' + self.org.name +
                        '/repos')

            total_items_rx = 0
            for page in self.org.hub.paginate(base_url, base_query):
                num_items_rx = len(page)
                total_items_rx += num_items_rx
                _LOG.debug('Server returned %s items; running total=%s items',
                           num_items_rx, total_items_rx)

                if not num_items_rx:
                    _LOG.debug('No more repositories.')
                    break

                for item in page:
                    yield item


class GitHubSearch(object):
    """GitHub /search v3 API wrapper"""

    def __init__(self, hub):
        """
        :param GitHub hub: GitHub root interface.
        """
        self._hub = hub

    def repositories(self):
        """Provide access to GitHub /search/repositories v3 API

        :return: GitHub repositories search interface
        :rtype: GitHubSearch.AllRepositoriesSearch
        """
        return self.AllRepositoriesSearch(self._hub)

    class AllRepositoriesSearch(object):
        """GitHub /search/repositories v3 API wrapper.

        See https://developer.github.com/v3/repos/
        """

        _URL_PATH = '/search/repositories'

        class _FilterArgs(object):
            """Supported Sort Queries"""
            # UNDEFINED = 0  # sort stat hasn't been set yet
            STARS = {'q': 'stars:>=0', 'sort': 'stars'}  # by number of stars
            FORKS = {'q': 'forks:>=0', 'sort': 'forks'}  # by number of forks

        def __init__(self, hub):
            """
            :param GitHub hub: `GitHub` root interface.
            """
            self._hub = hub
            self._sort_order = {'order': 'desc'}  # only support desc for now
            self._sort_query = None

        def get(self, max_items):
            """Creates a generator that runs the configured query and yields the
            requested items returned by the query as python dicts.

            :param int max_items: maximum number of items to return; non-
                negative.

            :rtype: generator
            """
            if not isinstance(max_items, numbers.Integral):
                raise TypeError(
                    'Expected int max_items but got {!r}'.format(max_items))

            if max_items < 0:
                raise ValueError(
                    'Expected non-negative max_items, but got {!r}'.format(
                        max_items))

            if self._sort_query is None:
                raise ValueError('Sort field not configured.')

            if max_items == 0:
                return

            base_url = (self._hub.BASE_API_URL + self._URL_PATH)

            base_query = {'per_page': 100}
            base_query.update(self._sort_order)
            base_query.update(self._sort_query)

            items_remaining = max_items

            for page in self._hub.paginate(base_url, base_query):
                num_items_rx = len(page['items'])
                _LOG.debug('Received %s items; ', num_items_rx)

                if page['incomplete_results']:
                    _LOG.debug('Query exceeded API time limit, response may be '
                               'incomplete.')

                if not page['items']:
                    _LOG.debug('No more repositories.')
                    return

                for item in page['items']:
                    items_remaining -= 1
                    yield item

                    if items_remaining <= 0:
                        return

        def by_stars(self):
            """Select starts as the sort field

            Example:
            https://api.github.com/search/repositories?q=stars:>=0&sort=stars&order=desc&page=1

            :returns: self so that configuration methods can be stacked
            :rtype: GitHubReposSearch
            :raises ValueError: if sort field is already configured
            """
            self._raise_if_sort_field_selected()
            self._sort_query = self._FilterArgs.STARS
            return self

        def by_forks(self):
            """Select forks as the sort field

            :returns: self so that configuration methods can be stacked
            :rtype: GitHubReposSearch
            """
            self._raise_if_sort_field_selected()
            self._sort_query = self._FilterArgs.FORKS
            return self

        def _raise_if_sort_field_selected(self):
            """Raise `ValueError` if sort field is already configured

            :raises ValueError: if sort field is already configured
            """
            if self._sort_query is not None:
                raise ValueError('Sort field is already selected.')
