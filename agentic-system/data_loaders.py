"""
Data loading functions for games and child profiles.
"""
from typing import Annotated
from langgraph.prebuilt import InjectedState
from states import State


def get_audio_book_by_id(state: Annotated[State, InjectedState]) -> str:
    """
    Return the audio book whose ID lives in state['audio_book_id'].

    :param state: state containing audio_book_id
    :return: description of game
    """
    # TODO LNG : Replace with real audio book content from s3 bucket instead.
    audio_book_id = state.get("audio_book_id", "0")
    game = {
        "0": "Du bist Lino, ein Teddybär und Erklärbär. Ein Erklärbar ist ganz schlau und kann Kindern ganz viele Sachen erklären. Immer wenn ein Kind eine Frage hat, kann das Kind mit der Frage zu dir kommen. Dann schaut ihr gemeinsam, ob ihr die Frage beantworten könnt.",
        "game-abc": "Der keine Drache Kokosnuss und der große Zauberer\n“"
                    "Kapitel 1\n"
                    "\n"
                    "Begegnung im Klippenwald\n"
                    "\n"
                    "Einmal im Jahr, wenn es Herbst wird auf der Dracheninsel und die Blätter der Bäume sich rot und gelb färben, gehen Kokosnuss und Matilda in den Klippenwald, um Pilze zu suchen. Heute sammeln sie den ganzen Tag über, bis ihre Körbe bis obenhin gefüllt sind mit den herrlichsten Pilzen. Gerade wollen sie sich auf den Rückweg machen, da hält Matilda ihre Nase in die Luft und schnüffelt.\n"
                    "»Was schnüffelst du denn?«, fragt Kokosnuss.\n"
                    "»Ich rieche Ziege«, antwortet Matilda.\n"
                    "Kokosnuss grinst: »Was ist denn mit deiner Nase los? Im Klippenwald gibt’s doch keine Ziegen!«\n"
                    "Matilda aber lässt ihren Korb stehen und marschiert in Richtung Ziegengeruch.\n"
                    "»Warte auf mich!«, ruft Kokosnuss.\n"
                    "Bald steigt auch ihm Ziegengeruch in die Nase. Die beiden bleiben wie angewurzelt stehen.\n"
                    "»Gibt’s ja nicht!«, flüstert Kokosnuss. »Eine echte Ziege, hier im Klippenwald!«\n"
                    "Durch ein paar Büsche hindurch sehen sie eine weiße Ziege, die verzweifelt versucht, eine Flasche zu öffnen. Die Flasche steckt im Wurzelwerk eines mächtigen Baumes.\n"
                    "»Verflixt noch mal!«, flucht die Ziege. »Dieser blöde Korken, diese bescheuerten Ziegenfüße!«\n"
                    "Kokosnuss und Matilda treten hinter dem Busch hervor: »Können wir dir helfen?«\n"
                    "Vor Schreck fällt die Ziege auf ihren Ziegenpopo: »Äh, wo kommt ihr denn her?«\n"
                    "»Vom Pilzesuchen«, antwortet Matilda. »Und wo kommst du her?«\n"
                    "Die Ziege mustert erst den jungen Feuerdrachen und dann das kleine Stachelschwein. Verstohlen blickt sie sich um.\n"
                    "»Könnt ihr ein Geheimnis für euch behalten?«\n"
                    "»Können wir.«\n"
                    "Ich bin in Wirklichkeit keine Ziege, sondern ein großer Zauberer.«\n"
                    "Kokosnuss und Matilda blicken sich an. Dann brechen sie in schallendes Gelächter aus. Sie müssen so lachen, dass sie sich am Waldboden kugeln.\n"
                    "Die Ziege ist empört: »Wenn ihr mir nicht glaubt, dann erzähle ich euch überhaupt nichts!«\n"
                    "Kokosnuss betrachtet die Ziege. Plötzlich kriegt er einen Schreck: »Bist du etwa der Zauberer Ziegenbart?«\n"
                    "»Ziegenbart? Bei allen Magiern des Erdkreises, ich doch nicht! Ich bin Holunder, Herr über das Flaschenland.\n"
                    "»Das Flaschenland?«\n"
                    "Da deutet die Ziege auf die Flasche: »Wenn ihr ganz genau hineinschaut, dann könnt ihr das Flaschenland sehen.«\n"
                    "Kokosnuss und Matilda blicken durch das grüne Glas ins Innere der Flasche. Und tatsächlich, wenn sie ganz nah heranrücken, erkennen sie, was die Ziege meint: ein winziges Land in einer Flasche!\n"
                    "»Bitte«, sagt Kokosnuss, »erzähl uns dein Geheimnis!«"
    }.get(audio_book_id, "This is an open world game. You can do anything you want.")
    return game


def get_child_profile(state: Annotated[State, InjectedState]) -> str:
    """
    Return the profile of the child whose ID lives in state['child_id'].

    :param state: state containing child_id
    :return: profile of child
    """
    child_id = state.get("child_id", "1")
    # TODO LNG : Replace with real child profile from s3 bucket instead.
    child_profile = {
        "1": "Das Kind ist 5 Jahre alt, mag Dinosaurier und Raketen. Es lernt gerade lesen und schreiben.",
        "2": "Das Kind ist 8 Jahre alt, mag Fussball und Videospiele. Es liest gerne Abenteuerbücher.",
        "3": "Das Kind ist 10 Jahre alt, mag Programmieren und Robotik. Es liest gerne Science-Fiction-Bücher.",
        "child-123": "Das Kind ist 7 Jahre alt, liebt Tiere und Natur. Es interessiert sich für Umweltschutz und liest gerne Sachbücher über Tiere.",
    }.get(child_id, "This is a child with no specific profile.")
    return child_profile
