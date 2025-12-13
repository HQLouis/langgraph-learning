"""
Node functions for the Lingolino graphs.
"""
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langgraph.types import Command
from states import State, BackgroundState
from data_loaders import get_audio_book_by_id, get_child_profile
from prompts import (getSpeechGrammarWorker_prompt, \
    getSpeechComprehensionWorker_prompt, getSprachhandlungAnalyseWorker_prompt, getSpeechVocabularyWorker_prompt,
                     getBoredomWorker_prompt, getFoerderfokusWorker_prompt, getAufgabenWorker_prompt, getSatzbauAnalyseWorker_prompt,
                     getSatzbauBegrenzungsWorker_prompt, getMasterPrompt)
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
    Streams responses chunk-by-chunk for low latency.

    :param state: Current state with messages and analysis
    :param llm: Language model instance
    :return: Updated state with new message
    """
    # TODO LNG: This will be flexibly set via the game config in the future.
    system_context = f"""
    {getMasterPrompt()}
    
    Book story: {state.get('audio_book', '')}
    Aufgaben für das Kind: {state.get('aufgaben', '')}
    Satzbaubegrenzungen: {state.get('satzbaubegrenzung', '')}
    """
    system_message = SystemMessage(content=system_context)
    messages = [system_message] + state["messages"]

    # Stream the response chunk-by-chunk (no accumulation)
    # This allows format_response to process chunks incrementally
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

def speechGrammarWorker(state: BackgroundState, config, llm):
    """
    Analyzes the speech and grammar aspects of the conversation, based on that analysis creates possible task and interactions that teaches the child grammar playfully..

    :param state: Background state
    :param config: Configuration with thread_id
    :param llm: Language model instance
    :return: Command with grammar analysis update
    """
    system_message = SystemMessage(content=getSpeechGrammarWorker_prompt())

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
    return Command(update={"grammar_analysis": response.content})

def speechComprehensionWorker(state: BackgroundState, config, llm):
    """
    Analyzes the comprehension aspects of the conversation and creates  impulses that support the child's understanding.

    :param state: Background state
    :param config: Configuration with thread_id
    :param llm: Language model instance
    :return: Command with speech comprehension analysis update
    """
    system_message = SystemMessage(content=getSpeechComprehensionWorker_prompt())

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
    return Command(update={"speech_comprehension_analysis": response.content})

def sprachhandlungsAnalyseWorker(state: BackgroundState, config, llm):
    """
    Analyzes the interaction aspects of the conversation, based on that creates task that encourage the child's interaction.

    :param state: Background state
    :param config: Configuration with thread_id
    :param llm: Language model instance
    :return: Command with interaction analysis update
    """
    system_message = SystemMessage(content=getSprachhandlungAnalyseWorker_prompt())

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
    return Command(update={"sprachhandlung_analysis": response.content})


def speechVocabularyWorker(state: BackgroundState, config, llm):
    """
    Analyzes the speech and vocabulary aspects of the conversation. Based on that analysis creates possible tasks and interactions to support vocabulary development.

    :param state: Background state
    :param config: Configuration with thread_id
    :param llm: Language model instance
    :return: Command with vocabulary analysis update
    """
    system_message = SystemMessage(content=getSpeechVocabularyWorker_prompt())

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
    return Command(update={"vocabulary_analysis": response.content})


def boredomWorker(state: BackgroundState, config, llm):
    """
    Analyzes the overall conversation to provide boredom analysis and suggestions.

    :param state: Background state
    :param config: Configuration with thread_id
    :param llm: Language model instance
    :return: Command with boredom analysis update
    """
    system_message = SystemMessage(content=getBoredomWorker_prompt())

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
    return Command(update={"boredom_analysis": response.content})

def foerderfokusWorker(state: BackgroundState, config, llm):
    """
    Analyzes the overall Förderfokus of the interaction to provide advice and suggestion for higher educational value of the total interaction.
    This worker uses the context of the grammer, comprehension, interaction, vocabulary analysis, boredom analysis to give an overall recommendation.

    :param state: Background state
    :param config: Configuration with thread_id
    :param llm: Language model instance
    :return: Command with förderfokus analysis update
    """
    system_message = SystemMessage(content=getFoerderfokusWorker_prompt())

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
    return Command(update={"foerderfokus": response.content})

def aufgabenWorker(state: BackgroundState, config, llm):
    """
    This worker suggest possible Aufgaben (tasks) based on the analysis of the Förderfokus worker to support the child's learning process.

    :param state: Background state
    :param config: Configuration with thread_id
    :param llm: Language model instance
    :return: Command with task suggestions update
    """
    system_message = SystemMessage(content=getAufgabenWorker_prompt())

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
    return Command(update={"aufgaben": response.content})


def satzbauAnalyseWorker(state: BackgroundState, config, llm):
    """
    Analyzes the overall conversation to analyze sentence structure and provide suggestions.

    :param state: Background state
    :param config: Configuration with thread_id
    :param llm: Language model instance
    :return: Command with satzbau analysis update
    """
    system_message = SystemMessage(content=getSatzbauAnalyseWorker_prompt())

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
    return Command(update={"satzbau_analysis": response.content})

def satzbauBegrenzungsWorker(state: BackgroundState, config, llm):
    """
    Uses the Satzbau-Analyse-Worker's results to create constraints for sentence structure in future interactions.

    :param state: Background state
    :param config: Configuration with thread_id
    :param llm: Language model instance
    :return: Command with satzbaubegrenzung update
    """
    system_message = SystemMessage(content=getSatzbauBegrenzungsWorker_prompt())

    # Analyze the conversation without participating in it
    conversation_summary = "\n".join([
        f"{msg.type}: {msg.content}" for msg in get_messages_history_from_immediate_graph_state(config)
    ])
    satzbau_analyse = state.get('satzbau_analysis', '')
    analysis_message = HumanMessage(
        content=f"Satzbau analyse: {satzbau_analyse}"
    )

    response = llm.invoke([system_message, analysis_message])
    # Store analysis separately from conversation
    return Command(update={"satzbaubegrenzung": response.content})

def initialStateLoader(state: State) -> dict:
    """
    Load initial state values such as audio book and child profile based on IDs in the state.

    :param state: current state
    :return: updated state with audio_book and child_profile
    """
    audio_book = get_audio_book_by_id(state)
    child_profile = get_child_profile(state)
    return Command(update={
        "audio_book": audio_book,
        "child_profile": child_profile
    })


def immediate_graph_needs_initial_state(state: State):
    """Check if immediate graph needs to load initial state."""
    if not (state.get("audio_book") and state.get("child_profile")):
        return "initialStateLoader"
    return "load_analysis"


def background_graph_needs_initial_state(state: State):
    """Check if background graph needs to load initial state."""
    if not (state.get("audio_book") and state.get("child_profile")):
        return "initialStateLoader"
    return ["speechGrammarWorker", "speechComprehensionWorker", "sprachhandlungsAnalyseWorker", "speechVocabularyWorker",
            "boredomWorker", "satzbauAnalyseWorker"]


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
        "aufgaben": snapshot.values.get("aufgaben", ""),
        "satzbaubegrenzung": snapshot.values.get("satzbaubegrenzung", ""),
    }
    return analyses
