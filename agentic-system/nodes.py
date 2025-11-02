"""
Node functions for the Lingolino graphs.
"""
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage, RemoveMessage
from langgraph.types import Command
from states import State, BackgroundState
from data_loaders import get_game_by_id, get_child_profile
from worker_prompts import speechVocabularyWorker_prompt, speechGrammarWorker_prompt, speechInteractionWorker_prompt, \
    speechComprehensionWorker_prompt, boredomWorker_prompt
from master_prompts import master_prompt
from typing import Any


# Global reference to background_graph (will be set after import)
background_graph: Any = None


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
    # TODO LNG: This will be flexibly set via the game config in the future.
    system_context = f"""
    {master_prompt}
    
    Book story: {state.get('game_description', '')}
    Vocabulary Analysis: {state.get('vocabulary_analysis', '')}
    Grammar Analysis: {state.get('grammar_analysis', '')}
    Interaction Analysis: {state.get('interaction_analysis', '')}
    Comprehension Analysis: {state.get('comprehension_analysis', '')}
    Boredom Analysis: {state.get('boredom_analysis', '')}
    
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
    # If the background graph hasn't been set yet, return an empty history
    if background_graph is None:
        return []
    # Ensure the background_graph exposes get_state before calling it
    if not hasattr(background_graph, 'get_state'):
        return []
    snapshot = background_graph.get_state({"configurable": {"thread_id": base_id}})
    messages = snapshot.values.get("messages", [])
    return messages


def speechVocabularyWorker(state: BackgroundState, config, llm):
    """
    Analyzes the speech and vocabulary aspects of the conversation. Based on that analysis creates possible tasks and interactions to support vocabulary development.

    :param state: Background state
    :param config: Configuration with thread_id
    :param llm: Language model instance
    :return: Command with speech analysis update
    """
    system_message = SystemMessage(content=speechVocabularyWorker_prompt)

    # Analyze the conversation without participating in it
    conversation_summary = "\n".join([
        f"{msg.type}: {msg.content}" for msg in get_messages_history_from_immediate_graph_state(config)
    ])
    child_profile = state.get('child_profile', '')
    game_description = state.get('game_description', '')
    analysis_message = HumanMessage(
        content=f"Analyze this conversation: {conversation_summary}. Child profile: {child_profile} Game description: {game_description}"
    )

    response = llm.invoke([system_message, analysis_message])
    # Store analysis separately from conversation
    return Command(update={"vocabulary_analysis": response.content})


def speechGrammarWorker(state: BackgroundState, config, llm):
    """
    Analyzes the speech and grammar aspects of the conversation, based on that analysis creates possible task and interactions that teaches the child grammar playfully..

    :param state: Background state
    :param config: Configuration with thread_id
    :param llm: Language model instance
    :return: Command with speech analysis update
    """
    system_message = SystemMessage(content=speechGrammarWorker_prompt)

    # Analyze the conversation without participating in it
    conversation_summary = "\n".join([
        f"{msg.type}: {msg.content}" for msg in get_messages_history_from_immediate_graph_state(config)
    ])
    child_profile = state.get('child_profile', '')
    game_description = state.get('game_description', '')
    analysis_message = HumanMessage(
        content=f"Analyze this conversation: {conversation_summary}. Child profile: {child_profile} Game description: {game_description}"
    )

    response = llm.invoke([system_message, analysis_message])
    # Store analysis separately from conversation
    return Command(update={"grammar_analysis": response.content})


def speechInteractionWorker(state: BackgroundState, config, llm):
    """
    Analyzes the interaction aspects of the conversation, based on that creates task that encourage the child's interaction.

    :param state: Background state
    :param config: Configuration with thread_id
    :param llm: Language model instance
    :return: Command with interaction analysis update
    """
    system_message = SystemMessage(content=speechInteractionWorker_prompt)

    # Analyze the conversation without participating in it
    conversation_summary = "\n".join([
        f"{msg.type}: {msg.content}" for msg in get_messages_history_from_immediate_graph_state(config)
    ])
    child_profile = state.get('child_profile', '')
    game_description = state.get('game_description', '')
    analysis_message = HumanMessage(
        content=f"Analyze this conversation: {conversation_summary}. Child profile: {child_profile} Game description: {game_description}"
    )

    response = llm.invoke([system_message, analysis_message])
    # Store analysis separately from conversation
    return Command(update={"interaction_analysis": response.content})


def speechComprehensionWorker(state: BackgroundState, config, llm):
    """
    Analyzes the comprehension aspects of the conversation and creates  impulses that support the child's understanding.

    :param state: Background state
    :param config: Configuration with thread_id
    :param llm: Language model instance
    :return: Command with comprehension analysis update
    """
    system_message = SystemMessage(content=speechComprehensionWorker_prompt)

    # Analyze the conversation without participating in it
    conversation_summary = "\n".join([
        f"{msg.type}: {msg.content}" for msg in get_messages_history_from_immediate_graph_state(config)
    ])
    child_profile = state.get('child_profile', '')
    game_description = state.get('game_description', '')
    analysis_message = HumanMessage(
        content=f"Analyze this conversation: {conversation_summary}. Child profile: {child_profile} Game description: {game_description}"
    )

    response = llm.invoke([system_message, analysis_message])
    # Store analysis separately from conversation
    return Command(update={"comprehension_analysis": response.content})


def boredomWorker(state: BackgroundState, config, llm):
    """
    Analyzes the overall conversation to provide boredom analysis and suggestions.

    :param state: Background state
    :param config: Configuration with thread_id
    :param llm: Language model instance
    :return: Command with border analysis update
    """
    system_message = SystemMessage(content=boredomWorker_prompt)

    # Analyze the conversation without participating in it
    conversation_summary = "\n".join([
        f"{msg.type}: {msg.content}" for msg in get_messages_history_from_immediate_graph_state(config)
    ])
    child_profile = state.get('child_profile', '')
    game_description = state.get('game_description', '')
    analysis_message = HumanMessage(
        content=f"Analyze this conversation: {conversation_summary}. Child profile: {child_profile} Game description: {game_description}"
    )

    response = llm.invoke([system_message, analysis_message])
    # Store analysis separately from conversation
    return Command(update={"boredom_analysis": response.content})


def format_response(state: State, llm) -> dict:
    """
    Formats the response of the agent to make it suitable for TTS without calling an LLM.
    Removes all emojis and line breaks from the last message and returns an updated
    messages list that removes the raw message and adds the cleaned one.
    :param state: Current state
    :param llm: (ignored) kept for compatibility
    :return: Dict containing messages to apply (RemoveMessage and AIMessage)
    """
    import re
    import emoji

    messages = state.get("messages", [])
    if not messages:
        # Nothing to format
        return {}

    raw_msg = messages[-1]
    # Support both dict-like messages and objects with attributes
    if isinstance(raw_msg, dict):
        raw_response = raw_msg.get("content", "")
        raw_message_id = raw_msg.get("id")
    else:
        raw_response = getattr(raw_msg, "content", "")
        raw_message_id = getattr(raw_msg, "id", None)

    if raw_response is None:
        raw_response = ""

    # Remove all emojis using the emoji library for comprehensive coverage
    without_emoji = emoji.replace_emoji(str(raw_response), replace='')

    # Remove all line breaks and collapse consecutive whitespace to single spaces
    single_line = re.sub(r"[\r\n]+", " ", without_emoji)
    single_line = re.sub(r"\s+", " ", single_line).strip()

    out_messages = []
    if raw_message_id is not None:
        out_messages.append(RemoveMessage(id=raw_message_id))
    out_messages.append(AIMessage(content=single_line))

    return {"messages": out_messages}

def initialStateLoader(state: State) -> dict:
    """
    Load initial state values such as game description and child profile based on IDs in the state.

    :param state: current state
    :return: updated state with game_description and child_profile
    """
    game_description = get_game_by_id(state)
    child_profile = get_child_profile(state)
    return Command(update={
        "game_description": game_description,
        "child_profile": child_profile
    })


def immediate_graph_needs_initial_state(state: State):
    """Check if immediate graph needs to load initial state."""
    if not (state.get("game_description") and state.get("child_profile")):
        return "initialStateLoader"
    return "load_analysis"


def background_graph_needs_initial_state(state: State):
    """Check if background graph needs to load initial state."""
    if not (state.get("game_description") and state.get("child_profile")):
        return "initialStateLoader"
    return ["speechVocabularyWorker", "speechGrammarWorker", "speechInteractionWorker", "speechComprehensionWorker", "boredomWorker"]


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
        "vocabulary_analysis": snapshot.values.get("vocabulary_analysis", ""),
        "grammar_analysis": snapshot.values.get("grammar_analysis", ""),
        "interaction_analysis": snapshot.values.get("interaction_analysis", ""),
        "comprehension_analysis": snapshot.values.get("comprehension_analysis", ""),
        "boredom_analysis": snapshot.values.get("boredom_analysis", "")
    }
    return analyses
