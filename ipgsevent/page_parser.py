from bs4 import BeautifulSoup
import urllib.request

from ipgsevent.base import (
    SeminarItem,
    validate_language,
    validate_bool,
    save_ics_file,
    parse_seminar_date,
    split_author_affiliation,
    prepare_email_annoucements,
)

URL = "http://eost.u-strasbg.fr/semipgs/calendar.html"


def parse_seminar_row(tr):
    seminar = SeminarItem()
    for td in tr.find_all("td"):
        try:
            td_class = td.attrs["class"][0]
        except KeyError:
            return None

        if td_class == "date":
            seminar.date = parse_seminar_date(td.text)
        elif td_class == "place":
            seminar.place = td.text.strip()
        elif td_class == "author":
            seminar.author, seminar.affiliation = split_author_affiliation(td.text)
        elif td_class == "title":
            seminar.title = td.text.strip()
            if seminar.title == "TBA":
                print("Skipping, the title not announced")
                print(seminar)
                return None
    return seminar


def parse_seminar_calendar_webpage():
    page = urllib.request.urlopen(URL)
    soup = BeautifulSoup(page, "html.parser")
    future_seminars = []

    for tr in soup.find_all("tr"):
        if "Past Seminars" in tr.find("p").text:
            break
        elif "Forthcoming Seminars" in tr.find("p").text:
            continue
        elif "Date,\xa0heure" in tr.find("p").text:
            continue

        seminar = parse_seminar_row(tr)
        if seminar is None:
            continue
        future_seminars.append(seminar)

    return future_seminars


def main():
    print("Parsing seminars calendar")
    future_seminars = parse_seminar_calendar_webpage()
    found_no = len(future_seminars)

    print(f"{found_no} seminars found. Which would you like to work on?")

    while True:
        for i, seminar in enumerate(future_seminars):
            print(f"{i}   --   {seminar}")

        selected_seminar = input("Select no of seminar\n")
        try:
            selected_seminar = int(selected_seminar)
            if selected_seminar >= found_no:
                raise ValueError
        except:
            ValueError(f"You have to provide number from 0 to {found_no-1}")

        seminar = future_seminars[selected_seminar]
        print(f"Working on {seminar}")

        seminar.detect_language()
        print(
            f"On the basis of title, language of seminar was set to {seminar.language}"
        )
        lang_to_set = input("Do you want to change it? Default: No \n")
        try:
            if lang_to_set == "":
                lang_to_set = "n"
            validate_language(lang_to_set)
            seminar.set_language(lang_to_set)
        except ValueError:
            print("Unexpected language entered, staying with auto-detected")

        save = input("Do you want to save .ics file? Default: Yes\n")
        if save == "":
            save = "y"
        if validate_bool(save):
            filepath = save_ics_file(seminar)
            print(f"File saved to {filepath}")

        if validate_bool(input("Compose emails in thunderbird?\n")):
            prepare_email_annoucements(seminar, filepath)

        if not validate_bool(
            input(
                "Seminar processing finished. Do you want to continue with different one?"
            )
        ):
            break

    print("Exiting. Bye")


if __name__ == "__main__":
    main()
