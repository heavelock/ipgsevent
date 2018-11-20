import feedparser
import re
from collections import namedtuple
import arrow
import dateparser


FEED_URL = 'http://eost.unistra.fr/agenda/seminaires-ipgs/?type=100'
PATTERN = ';|, |</span>|<span id="messageContent">|<br />|\n'


feed = feedparser.parse(FEED_URL)

Seminar = namedtuple('Seminar', ['title', 'date', 'speaker', 'language', 'location'])

for entry in feed['entries']:
    title = entry['title']

    summary = [x.strip() for x in re.split(PATTERN, entry['summary']) if x is not ""]

    starttime = dateparser.parse(' '.join(summary[1:3]))

    print(starttime)
    print('\n')

    Seminar(title=title, date=starttime, speaker)
