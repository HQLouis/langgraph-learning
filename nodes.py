"""
Node functions for the Lingolino graphs.
"""
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage, RemoveMessage
from langgraph.types import Command
from states import State, BackgroundState
from data_loaders import get_game_by_id, get_child_profile


# Global reference to background_graph (will be set after import)
background_graph = None


def set_background_graph(graph):
    """Set the background graph reference for cross-graph communication."""
    global background_graph
    background_graph = graph


def masterChatbot(state: State, llm):
    """
    Main chatbot node that generates responses to the child.

    :param state: Current state with messages and analysis
    :param llm: Language model instance
    :return: Updated state with new message
    """
    system_context = f"""
    You are chatting with a child. Your output shall consider the guidance's and be the direct answer to the child.  Try to keep the story engaging and fun. For that if needed even go into a different direction if the educational analysis suggests that the child is bored.
    Use this guidance:
    
    Story Analysis: {state.get('story_analysis', '')}
    Educational Analysis: {state.get('educational_analysis', '')}
    """
    system_message = SystemMessage(content=system_context)
    messages = [system_message] + state["messages"]

    # Stream the response
    response_content = ""
    for chunk in llm.stream(messages):
        if hasattr(chunk, 'content'):
            response_content += chunk.content

    return {"messages": [AIMessage(content=response_content)]}


def get_messages_history_from_immediate_graph_state(config) -> list:
    """
    Retrieve the message history from the immediate response graph's state.
    This function assumes that the immediate graph's state is accessible.

    :param config: Configuration with thread_id
    :return: List of messages from the immediate graph's state
    """
    # Fetch the immediate-thread snapshot
    base_id = config["configurable"]["thread_id"].rsplit("_", 1)[0]
    snapshot = background_graph.get_state({"configurable": {"thread_id": base_id}})
    messages = snapshot.values.get("messages", [])
    return messages


educational_prompt = (
    "You are a educational advisor. Analyze the following conversation between an application and a child.\n"
    "Provide analysis of:\n"
    "1. Child's current emotional state\n"
)


def educationalWorker(state: BackgroundState, config, llm):
    """
    Analyzes the educational aspects of the conversation.

    :param state: Background state
    :param config: Configuration with thread_id
    :param llm: Language model instance
    :return: Command with educational analysis update
    """
    system_message = SystemMessage(content=educational_prompt)

    # Analyze the conversation without participating in it
    conversation_summary = "\n".join([
        f"{msg.type}: {msg.content}" for msg in get_messages_history_from_immediate_graph_state(config)
    ])
    child_profile = state.get('child_profile', '')
    analysis_message = HumanMessage(
        content=f"Analyze this conversation: {conversation_summary}. Child profile: {child_profile}"
    )

    response = llm.invoke([system_message, analysis_message])
    # Store analysis separately from conversation
    return Command(update={"educational_analysis": response.content})


storytelling_prompt = (
    "You are a storytelling advisor. Analyze the following conversation between an application and a child.\n"
    "Provide three next story developments which makes sense to build a fun and engaging story.\n\n"
)


def storytellingWorker(state: BackgroundState, config, llm):
    """
    Analyzes the storytelling aspects and suggests story developments.

    :param state: Background state
    :param config: Configuration with thread_id
    :param llm: Language model instance
    :return: Command with story analysis update
    """
    system_message = SystemMessage(content=storytelling_prompt)

    # Analyze the conversation without participating in it
    conversation_summary = "\n".join([
        f"{msg.type}: {msg.content}" for msg in get_messages_history_from_immediate_graph_state(config)
    ])
    child_profile = state.get('child_profile', '')
    game_description = state.get('game_description', '')
    analysis_message = HumanMessage(
        content=f"Analyze this conversation: {conversation_summary} Child profile: {child_profile} Game description: {game_description}"
    )

    # Use invoke instead of stream for background processing - no need for streaming
    response = llm.invoke([system_message, analysis_message])
    # Store analysis separately from conversation
    return Command(update={"story_analysis": response.content})


def format_response(state: State, llm) -> dict:
    """
    Formats the response of the agent to make it suitable for TTS.
    This shall be the last step before returning the response to the user.
    Removes the raw response from state to avoid overloading it.

    :param state: Current state
    :param llm: Language model instance
    :return: Formatted string of response and removal of raw message
    """
    raw_response = state["messages"][-1].content
    raw_message_id = state["messages"][-1].id

    # Stream the formatted response
    formatted_content = ""
    for chunk in llm.stream([
        SystemMessage(content=(
            "You are a formatting assistant. Format the following text to be suitable "
            "for TTS. Remove all special characters such as emojis and make it easy to read aloud."
        )),
        HumanMessage(content=raw_response)
    ]):
        if hasattr(chunk, 'content') and chunk.content:
            formatted_content += chunk.content

    # Return both the formatted message and removal of the raw message
    return {
        "messages": [
            RemoveMessage(id=raw_message_id),  # Remove the raw response
            AIMessage(content=formatted_content)        # Add the formatted response
        ]
    }


def initialStateLoader(state: State) -> dict:
    """
    Load initial state values such as game description and child profile based on IDs in the state.

    :param state: current state
    :return: updated state with game_description and child_profile
    """
    game_description = get_game_by_id(state)
    child_profile = get_child_profile(state)
    return {
        "game_description": game_description,
        "child_profile": child_profile
    }


def immediate_graph_needs_initial_state(state: State):
    """Check if immediate graph needs to load initial state."""
    if not (state.get("game_description") and state.get("child_profile")):
        return "initialStateLoader"
    return "load_analysis"


def background_graph_needs_initial_state(state: State):
    """Check if background graph needs to load initial state."""
    if not (state.get("game_description") and state.get("child_profile")):
        return "initialStateLoader"
    return ["educationalWorker", "storytellingWorker"]


def load_analysis(state: State, config, background_graph_instance) -> dict:
    """
    Load analysis results from the background graph's state into the immediate graph's state.

    :param state: Current state
    :param config: Configuration with thread_id
    :param background_graph_instance: Instance of the background graph
    :return: updated state with analysis results
    """
    # TODO LNG: Make this conditional executed e.g. every third interaction.
    # TODO LNG: Add conditional edge if this node takes to much time.
    bg_thread_id = config["configurable"]["thread_id"] + "_analysis"
    snapshot = background_graph_instance.get_state({
        "configurable": {"thread_id": bg_thread_id}
    })
    analyses = {
        "story_analysis": snapshot.values.get("story_analysis", ""),
        "educational_analysis": snapshot.values.get("educational_analysis", "")
    }
    return analyses
