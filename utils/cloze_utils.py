import re
from typing import List

CLOZE_REGEX = re.compile(r"{{c\d+::.*?}}", re.MULTILINE | re.DOTALL)

def iscloze(text: str) -> bool:
    "returns True or False depending on if the text is a cloze note"
    if "}}" not in text:
        return False

    if not re.sub(CLOZE_REGEX, "", text).strip():
        return False

    if not re.search(CLOZE_REGEX, text):
        return False

    return True

def getclozes(text: str) -> List[str]:
    "return the cloze found in the text. Should only be called on cloze notes"
    assert iscloze(text), f"Text '{text}' does not contain a cloze"
    return re.findall(CLOZE_REGEX, text)


def cloze_input_parser(cloze: str) -> str:
    """edit the cloze from anki before sending it to the LLM. This is useful
    if you use weird formatting that mess with LLMs.
    If the note content is not a cloze, then return it unmodified."""
    if not iscloze(cloze):
        return cloze

    cloze = cloze.replace("\xa0", " ")

    # make newlines consistent
    cloze = cloze.replace("<br/>", "<br>")
    cloze = cloze.replace("\r", "<br>")
    cloze = cloze.replace("<br>", "\n")

    # make spaces consitent
    cloze = cloze.replace("&nbsp;", " ")

    # misc
    cloze = cloze.replace("&gt;", ">")
    cloze = cloze.replace("&ge;", ">=")
    cloze = cloze.replace("&lt;", "<")
    cloze = cloze.replace("&le;", "<=")

    assert iscloze(cloze), f"Invalid cloze: {cloze}"

    return cloze


def cloze_output_parser(cloze: str) -> str:
    """
    formats the cloze that were made easy to read by the LLM easy to
    display and answer in anki"""
    # strip
    cloze = cloze.strip()

    # make sure all newlines are consistent for now
    # TODO: You mean <br/>?
    cloze = cloze.replace("</br>", "<br>")
    cloze = cloze.replace("<br/>", "<br>")
    cloze = cloze.replace("\r", "<br>")
    # TODO: Not needed
    # cloze = cloze.replace("<br>", "\n")

    # make sure all spaces are consistent
    cloze = cloze.replace("&nbsp;", " ")

    # now use anki formatting for the newlines
    cloze = cloze.replace("\n", "<br>")

    return cloze
