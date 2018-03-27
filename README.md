# yagpy
Yet Another GitHub v3 Python API

## Portability

* Python 2.7.x and 3.4+ (tested on 2.7.10 and 3.6.4 on OS X)
* Linux, OS X (and probably Windows)


## Developer Editable Installation

From `yagpy` root directory, execute:

    `pip install -e .`

NOTE: If not using virtualenv on OS X, you might need to use the `--user` option
with `pip`.


## GitHub Request Rate Limits and Basic Authentication

See https://developer.github.com/v3/#rate-limiting

Unauthenticated GitHub API requests are subjected to severe rate limits. Using
`pulls` and `contrib-ratio` features of the command-line tool on a production
organization will almost certainly trigger rate limit errors.

This tool supports basic authentication via command-line optional arg
`--basic-auth` as well as via configuration file. Run `ghtoporgrepos --help`
for more details.


## Executing the command-line tool

The project's `setup.py` (used by te `pip` command above) installs the console
script `ghtoporgrepos`; assuming that `pip`'s `bin` installation directory is in
your `PATH`, you may run the tool this way:

    `ghtoporgrepos stars nodejs --max 10`
    `ghtoporgrepos forks nodejs --max 10`
    `ghtoporgrepos pulls nodejs --max 10 --basic-auth user:password`
    `ghtoporgrepos contrib-percent nodejs --max 10 --basic-auth user:password`

    `ghtoporgrepos --help`

```
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


## Testing

1. Install yagpy - see "Developer Editable Installation" above
2. Install nosetests:

    `pip install nose`

NOTE: If not using virtualenv on OS X, you might need to use the `--user` option
with `pip`.

From `yagpy` root directory, run the tests by executing:

    `nosetests`
