import datetime
import locale
import os
import threading
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

import arrow
import dateparser

import ics
from dateutil import tz

LOCALE_LOCK = threading.Lock()


@contextmanager
def setlocale(name):
    with LOCALE_LOCK:
        saved = locale.setlocale(locale.LC_ALL)
        try:
            yield locale.setlocale(locale.LC_ALL, name)
        finally:
            locale.setlocale(locale.LC_ALL, saved)


@dataclass
class SeminarItem:
    date: datetime.datetime = None
    author: str = None
    affiliation: str = None
    title: str = None
    language: str = "Français"
    place: str = "IPGS, Amphi Rothe"
    abstract: str = ""

    def set_language(self, language):
        self.language = validate_language(language)

    def detect_language(self):
        from textblob import TextBlob

        detected_lang = TextBlob(self.title).detect_language()
        self.set_language(detected_lang)


def validate_language(language):
    if language.strip().lower() in ("fr", "francais", "français", "french"):
        return "Français"
    elif language.strip().lower() in ("en", "english", "anglais"):
        return "Anglais"
    else:
        raise ValueError(f"Seminar can be either in fr or en, not {language}.")


def validate_bool(input):
    if input.lower() in ("f", "n", "false", "no", "0"):
        return False
    elif input.lower() in ("t", "y", "true", "yes", "1"):
        return True
    else:
        raise ValueError(f"Unexpected value for bool. Input was {input}")


def prepare_calendar_event(seminar):
    cal = ics.Calendar()
    event = ics.Event()
    event.begin = seminar.date
    event.name = seminar.title
    event.location = seminar.place
    description = "; ".join(
        [seminar.author, seminar.affiliation, seminar.language, seminar.abstract]
    )
    event.description = description
    cal.events.add(event)
    return cal


def prepare_output_filepath(seminar):
    filename_stem = "-".join(
        [str(seminar.date.date()), "Seminaire", seminar.author.split(" ")[1]]
    )
    default_output_filepath = Path(filename_stem).with_suffix(".ics")
    return default_output_filepath


def save_ics_file(seminar):

    default_output_filepath = prepare_output_filepath(seminar)
    filepath = input(
        f"Provide output filepath. Leave blank to use default. [Default: {default_output_filepath}]\n"
    )
    if filepath is "" or len(filepath) < 3:
        filepath = default_output_filepath
    else:
        filepath = Path(filepath)

    if filepath.exists():
        if not (validate_bool(input("File exists. Overwrite?"))):
            filepath = Path(filepath.stem + "_1").with_suffix(filepath.suffix)

    cal = prepare_calendar_event(seminar)

    with open(filepath, "w+") as f:
        f.writelines(cal)
    return filepath


def prepare_email_body(seminar):
    with setlocale("fr_FR"):
        email_body = f"""
        -------------- SEMINAIRE IPGS -------------------

        Intervenant :  {seminar.author}, {seminar.affiliation}

        Titre : {seminar.title}

        Salle : {seminar.place}

        Date : {seminar.date.strftime('%A %-d %B %Y').title()}, {seminar.date.strftime('%-Hh%M')}.

        Le séminaire sera en {seminar.language}.

        Ci-joint un fichier ics pour ajouter ce séminaire dans votre
        calendrier. Les renseignements sur les séminaires à venir sont sur la
        page
        http://eost.unistra.fr/agenda/seminaires-ipgs
        Espérant vous voir nombreux, nous vous souhaitons une bonne journée.
        Les responsables des séminaires de l’IPGS, Zacharie Duputel, Renaud
        Toussaint et les doctorants de deuxième année

        """
    return email_body


def prepare_compose_commands(seminar, email_body, filepath):
    seminaire_address = "seminaires@eost.unistra.fr"
    ipgs_address = "ipgs@unistra.fr"

    friday_before = (
        seminar.date.date()
        - datetime.timedelta(days=seminar.date.weekday())
        + datetime.timedelta(days=4, weeks=-1)
    )
    day_before = seminar.date.date() - datetime.timedelta(days=1)

    command_friday_before = f"thunderbird -compose \"to={seminaire_address},subject='[tous] [Séminaire IPGS] {seminar.author}, {seminar.affiliation}, {seminar.title}',body='{friday_before.strftime('%Y/%m/%d - 13:00')+email_body}',attachment='{filepath.absolute()}'\";"
    command_day_before = f"thunderbird -compose \"to={ipgs_address},subject='[tous] [Séminaire IPGS] [Demain] {seminar.author}, {seminar.affiliation}, {seminar.title}',body='{day_before.strftime('%Y/%m/%d - 13:00')+email_body}',attachment='{filepath.absolute()}'\";"
    command_same_day = f"thunderbird -compose \"to={ipgs_address},subject='[tous] [Séminaire IPGS] [Aujoud'hui] {seminar.author}, {seminar.affiliation}, {seminar.title}',body='{seminar.date.strftime('%Y/%m/%d - 08:00')+email_body}',attachment='{filepath.absolute()}'\";"

    script_filename = "open_drafts.sh"
    with open(script_filename, "w+") as f:
        f.write(command_friday_before)
        f.write(command_day_before)
        f.write(command_same_day)
    os.system(f"/bin/bash ./{script_filename}")
    Path(script_filename).unlink()
    return


def prepare_email_annoucements(seminar, filepath):
    email_body = prepare_email_body(seminar)
    prepare_compose_commands(seminar, email_body, filepath)


def parse_seminar_date(dtime):
    dtime = dateparser.parse(dtime)
    dtime = arrow.get(dtime)
    dtime = dtime.replace(tzinfo=tz.gettz())
    return dtime


def split_author_affiliation(author_affiliation_string):
    author_line = author_affiliation_string.split(",")
    author = author_line[0]
    affiliation = ", ".join(author_line[1:])
    return author.strip(), affiliation.strip()
