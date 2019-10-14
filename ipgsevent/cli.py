from ipgsevent.base import (
    SeminarItem,
    parse_seminar_date,
    validate_language,
    split_author_affiliation,
    save_ics_file,
    validate_bool,
    prepare_email_annoucements,
)


def main():

    seminar = SeminarItem()
    seminar_date = input("Date of the seminar yyyy/mm/dd\n").strip()
    seminar_hour = input("Starting hour of seminar (13h45)\n").strip()

    if seminar_hour is "":
        seminar_hour = "13h45"

    starttime = parse_seminar_date(" ".join([seminar_date, seminar_hour]))

    print(f"Got starttime: {starttime}")
    seminar.date = starttime

    while True:
        title = input("Title of seminar \n").strip()
        if title == "":
            print("Empty string received, repeat")
            continue
        seminar.title = title
        break

    while True:
        speaker = input("Speaker \n").strip()
        if speaker == "":
            print("Empty string received, repeat")
            continue
        seminar.author, seminar.affiliation = split_author_affiliation(speaker)

        print(
            f"Received:\n\tName: {seminar.author}\n\tAffiliation: {seminar.affiliation}"
        )
        break

    for i in range(2):
        lang = input("Language of seminar (french/english) \n").strip()
        try:
            lang = validate_language(language=lang)
        except ValueError as e:
            print(e)
            continue
        break

    print(f"Got language: {lang}")
    seminar.set_language(lang)

    location = input("Location of seminar (Amphi rothe) \n").strip()
    if location is "":
        location = "IPGS, Amphi Rothé"
    seminar.place = location

    abstract = input("Abstract (Optional)").strip()
    seminar.abstract = abstract

    save = input("Do you want to save .ics file? Default: Yes\n")
    if save == "":
        save = "y"
    if validate_bool(save):
        filepath = save_ics_file(seminar)
        print(f"File saved to {filepath}")

    if validate_bool(input("Compose emails in thunderbird?\n")):
        prepare_email_annoucements(seminar, filepath)


if __name__ == "__main__":
    main()
