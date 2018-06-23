import csv
import datetime
import json
import re
from pathlib import Path

import psycopg2

__all__ = ['Exporter']

# a regex that targets the .000000+00:00 part of a date string provided in
# messages.csv (the .000000 part is optional)
STRIP_DATE_REGEX = re.compile(r'(\.\d{6})?\+00:00')


class Exporter:

    def __init__(self, package_path, dsn):
        self.package_path = package_path
        self.dsn = dsn
        self.conn = psycopg2.connect(dsn)
        self.cur = self.conn.cursor()
        self.index = None

        self.load_index()

    @property
    def messages(self):
        return self.package_path / 'messages'

    def process_message(self, row):
        message_id, raw_date, message_content, _ = row

        # remove the microseconds (.000000) and utc offset (+00:00) from the
        # date string using a regex, as python's strptime cannot process these
        cleansed_date = STRIP_DATE_REGEX.sub('', raw_date)

        date = datetime.datetime.strptime(cleansed_date, '%Y-%m-%d %H:%M:%S')

        return message_id, date, message_content

    def load_index(self):
        with open(self.messages / 'index.json') as fp:
            self.index = json.load(fp)

    def prepare(self):
        self.cur.execute(
            '''
                CREATE TABLE IF NOT EXISTS messages (
                    channel_id BIGINT,
                    channel_type SMALLINT,
                    channel_name TEXT,
                    guild_id BIGINT,
                    guild_name TEXT,
                    recipients BIGINT[],
                    id BIGINT PRIMARY KEY,
                    date TIMESTAMP WITHOUT TIME ZONE,
                    content TEXT
                )
            '''
        )
        self.conn.commit()

    def insert_message(self, *, channel, message):
        m_id, date, content = message

        recipients = channel.get('recipients', None)  # group dms

        # extract guild information from channel.json, if any.
        guild = channel.get('guild', {})
        guild_id = guild.get('id', None)
        guild_name = guild.get('name', None)

        self.cur.execute(
            '''
                INSERT INTO messages
                (
                    channel_id, channel_type, channel_name,
                    guild_id, guild_name,
                    recipients,
                    id, date, content
                )
                VALUES (
                    %(channel_id)s, %(channel_type)s, %(channel_name)s,
                    %(guild_id)s, %(guild_name)s,
                    %(recipients)s,
                    %(id)s, %(date)s, %(content)s
                )
                ON CONFLICT (id) DO UPDATE SET
                    channel_name = EXCLUDED.channel_name
            ''',
            {
                'channel_id': channel['id'],
                'channel_type': channel['type'],
                'channel_name': channel['name'],
                'guild_id': guild_id,
                'guild_name': guild_name,
                'recipients': recipients,
                'id': m_id,
                'date': date,
                'content': content,
            }
        )

    def export(self):
        messages = self.package_path / 'messages'

        for channel_path in messages.iterdir():
            if channel_path.is_file():
                continue

            with open(channel_path / 'channel.json') as fp:
                channel = json.load(fp)

                # channel objects in channel.json don't have name fields, but
                # index.json does, so let's grab the name (if any) from
                # index.json and shove it in the channel.
                channel['name'] = self.index.get(str(channel['id']), None)

            with open(channel_path / 'messages.csv') as fp:
                reader = csv.reader(fp, delimiter=',')

                # ignore the first row of messages.csv which describes each
                # column
                rows = filter(lambda r: r[0] != 'ID', reader)

                # 'process' each row. all this really does is parse the date
                # by removing some cruft and passing it into strptime, which
                # converts strings into actual date objects
                messages = list(map(self.process_message, rows))

                total = len(messages)

                for (index, message) in enumerate(messages):
                    print(
                        '\r>> Exporting C#{} ({}/{}){}'.format(
                            channel_path.name, index, total, ' ' * 10
                        ), end=''
                    )

                    self.insert_message(channel=channel, message=message)

            # we're done with this channel, let's commit any changes to the
            # database
            self.conn.commit()

    def close(self):
        self.cur.close()
        self.conn.close()


if __name__ == '__main__':
    import sys

    _, raw_path, dsn = sys.argv
    path = Path(raw_path).resolve()

    exporter = Exporter(path, dsn)

    # let's create the necessary tables
    exporter.prepare()

    exporter.export()
    exporter.close()

    print('All done!')
