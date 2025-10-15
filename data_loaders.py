"""
Data loading functions for games and child profiles.
"""
from typing import Annotated
from langgraph.prebuilt import InjectedState
from states import State


def get_game_by_id(state: Annotated[State, InjectedState]) -> str:
    """
    Return the game description whose ID lives in state['game_id'].

    :param state: state containing game_id
    :return: description of game
    """
    game_id = state.get("game_id", "0")
    game = {
        "0": "Du bist Lino, ein Teddybär und Erklärbär. Ein Erklärbar ist ganz schlau und kann Kindern ganz viele Sachen erklären. Immer wenn ein Kind eine Frage hat, kann das Kind mit der Frage zu dir kommen. Dann schaut ihr gemeinsam, ob ihr die Frage beantworten könnt.",
    }.get(game_id, "This is an open world game. You can do anything you want.")
    print("Game loaded:", game)
    return game


def get_child_profile(state: Annotated[State, InjectedState]) -> str:
    """
    Return the profile of the child whose ID lives in state['child_id'].

    :param state: state containing child_id
    :return: profile of child
    """
    child_id = state.get("child_id", "1")
    child_profile = {
        "1": "Das Kind ist 5 Jahre alt, mag Dinosaurier und Raketen. Es lernt gerade lesen und schreiben.",
        "2": "Das Kind ist 8 Jahre alt, mag Fussball und Videospiele. Es liest gerne Abenteuerbücher.",
        "3": "Das Kind ist 10 Jahre alt, mag Programmieren und Robotik. Es liest gerne Science-Fiction-Bücher.",
    }.get(child_id, "This is a child with no specific profile.")
    print("Child profile loaded:", child_profile)
    return child_profile

