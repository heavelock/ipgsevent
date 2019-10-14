from bs4 import BeautifulSoup
import re
import urllib.request
import dateparser
import datetime
import ics
from pathlib import Path
import locale
import threading
import os
import subprocess
from contextlib import contextmanager
from dataclasses import dataclass

URL = 'http://eost.u-strasbg.fr/semipgs/calendar.html'

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
    language: str = 'Français'
    place: str = 'IPGS, Amphi Rothe'
    abstract: str = None

    def set_language(self, language):
        self.language = validate_language(language)

    def detect_language(self):
        from textblob import TextBlob
        detected_lang = TextBlob(self.title).detect_language()
        self.set_language(detected_lang)
        

def validate_language(language):
        if language.strip().lower() in ('fr', 'francais', 'français', 'french'):
            return 'Français'
        elif language.strip().lower() in ('en', 'english', 'anglais'):
            return 'Anglais'
        else:
            raise ValueError(f'Seminar can be either in fr or en, not {language}.')

def validate_bool(input):
    if input.lower() in ('f', 'n', 'false', 'no', '0'):
        return False
    elif input.lower() in ('t', 'y', 'true', 'yes', '1'):
        return True
    else:
        raise ValueError(f'Unexpected value for bool. Input was {input}')

def prepare_calendar_event(seminar):
    cal = ics.Calendar()
    event = ics.Event()
    event.begin = seminar.date
    event.name = seminar.title
    event.location = seminar.place
    description = "\n".join([
        seminar.author,
        seminar.affiliation,
        seminar.language,
    ])
    event.description = description
    cal.events.add(event)
    return cal


def prepare_output_filepath(seminar):
    filename_stem = '-'.join(
        [
            str(seminar.date.date()),
            'Seminaire',
            seminar.author.split(' ')[1]
        ]
    )
    default_output_filepath = Path(filename_stem).with_suffix('.ics')
    return default_output_filepath


def save_ics_file(seminar):
    
    default_output_filepath = prepare_output_filepath(seminar)
    filepath = input(f'Provide output filepath. Leave blank to use default. [Default: {default_output_filepath}]\n')
    if filepath is '' or len(filepath) <3:
        filepath = default_output_filepath
    else:
        filepath = Path(filepath)
    
    if filepath.exists():
        if not (validate_bool(input('File exists. Overwrite?'))):
            filepath = Path(filepath.stem+'_1').with_suffix(filepath.suffix)
                
    cal = prepare_calendar_event(seminar)

    with open(filepath, "w+") as f:
        f.writelines(cal)
    return filepath


def prepare_email_body(seminar):       
    with setlocale('fr_FR'):
        email_body = f'''
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

        '''
    return email_body

def prepare_compose_commands(seminar, email_body, filepath):
    seminaire_address = 'seminaires@eost.unistra.fr'
    ipgs_address = 'ipgs@unistra.fr'

    friday_before = (seminar.date.date() 
        - datetime.timedelta(days=seminar.date.weekday()) 
        + datetime.timedelta(days=4, weeks=-1)) 
    day_before = (seminar.date.date() - datetime.timedelta(days=1))

    command_friday_before = f"thunderbird -compose \"to={seminaire_address},subject='[tous] [Séminaire IPGS] {seminar.author}, {seminar.affiliation}, {seminar.title}',body='{friday_before.strftime('%Y/%m/%d - 13:00')+email_body}',attachment='{filepath.absolute()}'\";"   
    command_day_before = f"thunderbird -compose \"to={ipgs_address},subject='[tous] [Séminaire IPGS] [Demain] {seminar.author}, {seminar.affiliation}, {seminar.title}',body='{day_before.strftime('%Y/%m/%d - 13:00')+email_body}',attachment='{filepath.absolute()}'\";"   
    command_same_day = f"thunderbird -compose \"to={ipgs_address},subject='[tous] [Séminaire IPGS] [Aujoud'hui] {seminar.author}, {seminar.affiliation}, {seminar.title}',body='{seminar.date.strftime('%Y/%m/%d - 08:00')+email_body}',attachment='{filepath.absolute()}'\";"   

    script_filename = 'open_drafts.sh'
    with open(script_filename, 'w+') as f:
        f.write(command_friday_before)
        f.write(command_day_before)
        f.write(command_same_day)
    os.system(f'/bin/bash ./{script_filename}') 
    Path(script_filename).unlink()
    return


def parse_seminar_row(tr):
    seminar = SeminarItem()
    for td in tr.find_all('td'):
        try:
            td_class = td.attrs['class'][0]
        except KeyError:
            return None

        if td_class == 'date':
            seminar.date = dateparser.parse(td.text)
        elif td_class == 'place':
            seminar.place = td.text.strip()
        elif td_class == 'author':
            author_line = td.text.split(',')
            author = author_line[0]
            affiliation = ', '.join(author_line[1:])
            seminar.author = author.strip()
            seminar.affiliation = affiliation.strip()
        elif td_class == 'title':
            seminar.title = td.text.strip()
            if seminar.title == 'TBA':
                print('Skipping, the title not announced')
                print(seminar)
                return None
    return seminar
        
def parse_seminar_calendar_webpage():
    page = urllib.request.urlopen(URL)
    soup = BeautifulSoup(page, 'html.parser')
    finish_reading = False

    future_seminars = []

    for tr in soup.find_all('tr'):
        if 'Past Seminars' in tr.find('p').text:
            break
        elif 'Forthcoming Seminars' in tr.find('p').text:
            continue
        elif 'Date,\xa0heure' in tr.find('p').text:
            continue
        
        seminar = parse_seminar_row(tr)
        if seminar is None:
            continue
        future_seminars.append(seminar)

    return future_seminars
        


def main():
    print('Parsing seminars calendar')
    future_seminars = parse_seminar_calendar_webpage()
    found_no = len(future_seminars)

    print(f'{found_no} seminars found. Which would you like to work on?')
    

    while True:
        for i, seminar in enumerate(future_seminars):
            print(f'{i}   --   {seminar}')

        selected_seminar = input('Select no of seminar\n')
        try:
            selected_seminar = int(selected_seminar)
            if selected_seminar >= found_no:
                raise ValueError
        except:
            ValueError(f'You have to provide number from 0 to {found_no-1}')
    
        seminar = future_seminars[selected_seminar]
        print(f'Working on {seminar}')

        seminar.detect_language()
        print(f'On the basis of title, language of seminar was set to {seminar.language}')
        lang_to_set = input('Do you want to change it? Default: No \n')
        try:
            if lang_to_set == '':
                lang_to_set = 'n'
            validate_language(lang_to_set)
            seminar.set_language(lang_to_set)
        except ValueError:
            print("Unexpected language entered, staying with auto-detected")

        save = input('Do you want to save .ics file? Default: Yes\n')
        if save == '':
            save = 'y'
        if validate_bool(save):
            filepath = save_ics_file(seminar)
            print(f'File saved to {filepath}')
        
        if validate_bool(input('Compose emails in thunderbird?\n')):
            email_body = prepare_email_body(seminar)
            prepare_compose_commands(seminar, email_body, filepath)
            

        if not validate_bool(input('Seminar processing finished. Do you want to continue with different one?')):
           break
        
    print('Exiting. Bye')

    

if __name__ == "__main__":
    main()