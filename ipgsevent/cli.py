import click
import ics
import datetime
import dateparser
import arrow
from dateutil import tz

def main():
    cal = ics.Calendar()
    event = ics.Event()

    seminar_date = input("Date of the seminar yyyy/mm/dd").strip()
    seminar_hour = input("Starting hour of seminar").strip()


    title = input("Title of seminar").strip()
    speaker = input("Speaker").strip()
    lang = input("Language of seminar (french/english)").strip()
    location = input("Location of seminar").strip()
    abstract = input("Abstract (Optional)").strip()



    starttime = dateparser.parse(" ".join([seminar_date, seminar_hour]))
    starttime = arrow.get(starttime)
    starttime = starttime.replace(tzinfo=tz.gettz())



    event.begin = starttime
    event.name = title
    event.location = location

    if lang.lower() == "french":
        lang = "Français"
    elif lang.lower() == "english":
        lang = "Anglais"
    language = "Le séminaire sera en {}.".format(lang)


    description = "\n".join([speaker, language, abstract])

    event.description = description

    cal.events.add(event)

    filename_default = '-'.join([starttime.date(), 'Seminaire'])

    filename = input("Filename (Default: {})".format(filename_default)).strip()

    if filename == "":
        filename = filename_default


    with open(filename, "w+") as f:
        f.writelines(cal)



if __name__ == '__main__':
    main()