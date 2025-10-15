"""
State definitions for the Lingolino application.
"""
from typing import Annotated
from typing_extensions import TypedDict
from langgraph.graph.message import add_messages


class State(TypedDict):
    """Main state for the immediate response graph."""
    # Messages have the type "list". The `add_messages` function
    # in the annotation defines how this state key should be updated
    # (in this case, it appends messages to the list, rather than overwriting them)
    child_id: str
    game_id: str
    messages: Annotated[list, add_messages]
    game_description: str
    child_profile: str
    story_analysis: str
    educational_analysis: str


class BackgroundState(TypedDict):
    """State for the background analysis graph."""
    child_id: str
    game_id: str
    # TODO LNG: for the inputs below we will test if keeping the list of inputs is useful later.
    # For now go with the simple and promising variant of only having the most recent input in the state.
    game_description: str
    child_profile: str
    story_analysis: str
    educational_analysis: str

