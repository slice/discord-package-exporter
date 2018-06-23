# discord-package-exporter

This repository houses a Python 3 script that will export all messages from
your [Discord data package][ddp] into a [Postgresql][postgres] database.
Instructions showing the process of obtaining your data package are available
[here][ob].

[postgres]: https://www.postgresql.org/
[ob]:
https://support.discordapp.com/hc/en-us/articles/360004027692-Requesting-a-Copy-of-your-Data\
[ddp]: https://support.discordapp.com/hc/en-us/articles/360004957991-Your-Discord-Data-Package

## Usage

This script uses psycopg2 to connect to the Postgres database. Install
dependencies with `pip`:

```sh
$ pip3 install -U -r requirements.txt
```

Or, if you'd prefer, just install `psycopg2` manually with `pip3 install
psycopg2`.

This script assumes that you already have a Postgresql server setup on your
local machine. The script will automatically create any required tables for
you, but you still need to create a database (you can name it `discord`):

```sh
$ createdb discord
```

Once you have created the database, run the script:

```sh
$ python3 dpe.py "$HOME/discord-data-package" "dbname=discord user=postgres"
```

Like mentioned earlier, required tables will be created if they don't already
exist.

The first argument is a path to your Discord data package, while the second
argument is a [psycopg2 DSN (connection string)][connstr].

[connstr]: https://www.postgresql.org/docs/current/static/libpq-connect.html#LIBPQ-CONNSTRING

This process can take a few minutes. Progress will be shown in your terminal
while data is transferred.
