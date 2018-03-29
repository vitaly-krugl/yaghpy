# yagpy
Yet Another GitHub v3 Python API

See https://developer.github.com/v3/

**Table of Contents**
* [Portability](#portability)
* [Modules of Interest](#modules-of-interest)
* [Developer Editable Installation](#developer-editable-installation)
* [GitHub Request Rate Limits](#github-request-rate-limits)
* [Configuring GitHub Basic Authentication](#configuring-github-basic-authentication)
* [Executing the command-line tool](#executing-the-command-line-tool)
* [Running Tests](#running-tests)


## Portability

* Python 2.7.x and 3.4+ (tested with 2.7.10 and 3.6.4 on OS X)
* Linux, OS X (and probably Windows)


## Modules of Interest

`src/yagpy/`
* `top_org_repos.py`: implementation of the command-line tool with
`top_org_repos()` as console script entry point.
* `yagpy.py`: wrapper around GitHub v3 REST API for commmands needed by
`top_org_repos.py`.

`tests/acceptance/`
* `ghtoporgrepos_test.py`: Prototypical acceptance/integration tests for
commands supported by the command-line tool.


## Developer Editable Installation

To install `yagpy` in editable mode, execute this `pip` command from `yagpy`
root directory:
```
pip install -e .
```

NOTE: If not using virtualenv on OS X, you might need to use the `--user` option
with `pip`.


## GitHub Request Rate Limits

See https://developer.github.com/v3/#rate-limiting

Unauthenticated GitHub API requests are subjected to severe rate limits. Using
`pulls` and `contrib-ratio` features of the command-line tool on a production
organization will almost certainly trigger rate limit errors.

This tool supports basic authentication via command-line optional arg
--basic-auth as well as via configuration file. Run `ghtoporgrepos --help`
for more details.


## Configuring GitHub Basic Authentication

The command-line tool supports Basic Authentication using your GitHub username
and password. There are two ways to supply the authentication credentails:
1. Via command-line optional arg `--basic-auth=username:passwrod`
2. Via configuration file

If authentication credentials are not provided via `--basic-auth` command-line
arg, the tool looks for the configration file: first, it checks the environment
variable `YAGPY_CONFIG_PATH` - if it's defined, it's assumed to contain the
location of the config file on the filesystem. If `YAGPY_CONFIG_PATH` is not
set, the location defaults to `~/.yagpy/config`.

The yagpy configuration file has the following format:
```
# yagpy (yet another github API python wrapper) cofiguration
[default]
github_user=username
github_password="password"
```


## Executing the command-line tool

The project's `setup.py` (used by the [yagpy installation command](#developer-editable-installation))
installs the console script `ghtoporgrepos`; assuming that `pip`'s `bin`
installation directory containing `ghtoporgrepos` is in your `PATH`, you may run
the tool this way:

```
ghtoporgrepos stars nodejs --max 10
ghtoporgrepos forks nodejs --max 10
ghtoporgrepos pulls nodejs --max 10 --basic-auth user:password
ghtoporgrepos contrib-ratio nodejs --max 10 --basic-auth user:password

ghtoporgrepos --help

usage: ghtoporgrepos ACTION ORGANIZATION [-h] [--max MAX] [--basic-auth BASIC_AUTH]

Get top-N GitHub organization repositories meeting the given criteria.
Authentication credentials may provided either via the optional arg --basic-
auth or via config file at location referenced by the environment variable
YAGPY_CONFIG_PATH, defaulting to '~/.yagpy/config'. Unauthenticated access is
subject to severely reduced GitHub request rate quota limits and increased
command errors.

positional arguments:
  ACTION                contrib-ratio: Top-N repos by contribution ratio
                        (PRs/forks); forks: Top-N repos by number of forks;
                        pulls: Top-N repos by number of Pull Requests (PRs);
                        stars: Top-N repos by number of stars;
  ORGANIZATION          Name of GitHub organization.

optional arguments:
  -h, --help            show this help message and exit
  --basic-auth BASIC_AUTH
                        Colon-separated GitHub basic authentication
                        credentials (user:password). NOTE: user containing
                        colon character(s) is not supported.
  --max MAX             Maximum results to output [5].

```

## Running Tests

1. Install `yagpy` - see [Developer Editable Installation](#developer-editable-installation) above.
2. Install `nosetests`:
```
pip install nose
```

NOTE: If not using virtualenv on OS X, you might need to use the `--user` option
with `pip`.

From `yagpy` root directory, run the tests by executing (assuming `nosetsts`'
installation directory is in your `PATH`:

```
nosetests
```

The test output should look something like this:
```
test_top_repos_bad_arg (ghtoporgrepos_test.GitHubTopOrgReposTest) ... ok
test_top_repos_by_contrib_ratio (ghtoporgrepos_test.GitHubTopOrgReposTest) ... ok
test_top_repos_by_number_of_forks (ghtoporgrepos_test.GitHubTopOrgReposTest) ... ok
test_top_repos_by_number_of_pulls (ghtoporgrepos_test.GitHubTopOrgReposTest) ... ok
test_top_repos_by_number_of_stars (ghtoporgrepos_test.GitHubTopOrgReposTest) ... ok
test_top_repos_help (ghtoporgrepos_test.GitHubTopOrgReposTest) ... ok
```

----------------------------------------------------------------------
Ran 6 tests in 9.510s

OK
```
