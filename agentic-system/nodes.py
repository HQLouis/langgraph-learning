"""
Node functions for the Lingolino graphs.
"""
import logging
from pathlib import Path
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langgraph.types import Command
from states import State, BackgroundState
from data_loaders import get_audio_book_by_id, get_child_profile
from prompts import (getSpeechGrammarWorker_prompt, \
                     getSpeechComprehensionWorker_prompt, getSprachhandlungAnalyseWorker_prompt,
                     getSpeechVocabularyWorker_prompt,
                     getBoredomWorker_prompt, getFoerderfokusWorker_prompt, getAufgabenWorker_prompt,
                     getSatzbauAnalyseWorker_prompt,
                     getSatzbauBegrenzungsWorker_prompt, getMasterPrompt, getMasterFirstMessagePrompt)
from typing import Any, Optional
from config.conversation_termination_policy import get_termination_prompt, is_normal_phase, is_soft_termination_phase, \
    is_conversation_ended
from beats import BeatPackManager, BeatRetriever

# Initialize logger
logger = logging.getLogger(__name__)

# Global reference to background_graph (will be set after import)
background_graph: Any = None

# Global beat pack manager (will be initialized with content directory)
beat_manager: Optional[BeatPackManager] = None


def set_background_graph(graph):
    """Set the background graph reference for cross-graph communication."""
    global background_graph
    background_graph = graph


def initialize_beat_manager(content_dir: Path):
    """Initialize the global beat pack manager."""
    global beat_manager
    beat_manager = BeatPackManager(content_dir)
    logger.info(f"Initialized beat manager with content_dir: {content_dir}")

def masterChatbot(state: State, llm):
    """
    Main chatbot node that generates responses to the child.
    Streams responses chunk-by-chunk for low latency.

    :param state: Current state with messages and analysis
    :param llm: Language model instance
    :return: Updated state with new message
    """
    logger.info("masterChatbot: Starting to generate response")
    is_first_message = not any(isinstance(msg, AIMessage) for msg in state["messages"])

    message_count = len(state["messages"]) // 2  # Assuming each interaction has a user and bot message
    logger.info(f"masterChatbot: Processing message count: {message_count}, is_first_message: {is_first_message}")

    # TODO LNG: This will be flexibly set via the game config in the future.
    system_context = f"""
    {getMasterPrompt() if not is_conversation_ended(message_count) else ''}
    """

    if is_first_message:
        system_context += f"\n{getMasterFirstMessagePrompt()}"

    # Use beat context if available, otherwise fall back to full audio_book
    content_context = state.get('beat_context')
    if content_context:
        logger.info("masterChatbot: Using beat-based context (closed-world)")
        system_context += f"""
    
    [GESCHLOSSENES WELTWISSEN - STRIKTE EINHALTUNG]
    Verwende AUSSCHLIESSLICH die folgenden Beat-Inhalte als einzige inhaltliche Quelle.
    Erfinde KEINE neuen Fakten, Figuren, Orte oder Ereignisse außerhalb dieser Beats.
    
    {content_context}
    
    WICHTIG: Antworte NUR basierend auf den oben genannten Beats. Wenn das Kind nach etwas fragt, 
    das nicht in diesen Beats vorkommt, sage ehrlich: "Das weiß ich nicht genau aus der Geschichte."
    """
    else:
        logger.info("masterChatbot: Using full audio_book context (fallback)")
        system_context += f"""
    Verwende ausschließlich den expliziten Buchkontext sowie Inhalte, die sich eindeutig daraus ableiten lassen, als einzige inhaltliche Quelle für Figuren, Orte, Gegenstände und Ereignisse : {state.get('audio_book', '')}\n\n
    """

    system_message = SystemMessage(content=system_context)

    meta_system = SystemMessage(content=f"""
    [METAREGELN FÜR DIE NÄCHSTE ASSISTANT-ANTWORT — NICHT AN DAS KIND ADRESSIEREN]
    
    🎯 Aufgaben für das Kind:
    {state.get('aufgaben', 'Keine spezifischen Aufgaben.')}
    
    📏 Satzbaubegrenzungen (STRIKT EINHALTEN):
    {state.get('satzbaubegrenzung', 'Keine Begrenzungen.')}
    
    WICHTIG:
    - Antworte auf die LETZTE KIND-NACHRICHT im Verlauf.
    - Nutze die Regeln nur, um die Form deiner Antwort zu steuern.
    """)

    messages = [system_message]
    if is_normal_phase(message_count) and (state.get('aufgaben') or state.get('satzbaubegrenzung')):
        messages.append(meta_system)
        logger.info(f"masterChatbot: Added meta_system with aufgaben and satzbaubegrenzung")
    if not is_normal_phase(message_count):
        termination_prompt = get_termination_prompt(message_count)
        termination_system = SystemMessage(content=f"""
        [GESPRÄCHSBEENDIGUNGSRICHTLINIEN — NICHT AN DAS KIND ADRESSIEREN]
        
        {termination_prompt}
        """)
        messages.append(termination_system)
        logger.info(f"masterChatbot: Added termination prompt for message count: {message_count}")

    messages += state["messages"]

    # Stream the response chunk-by-chunk (no accumulation)
    # This allows format_response to process chunks incrementally
    logger.info("masterChatbot: Starting LLM stream")
    response_content = ""
    for chunk in llm.stream(messages):
        if hasattr(chunk, 'content'):
            response_content += chunk.content

    logger.info(f"masterChatbot: Generated response with length: {len(response_content)}")
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
    logger.info("speechGrammarWorker: Starting grammar analysis")
    system_message = SystemMessage(content=getSpeechGrammarWorker_prompt())

    # Analyze the conversation without participating in it
    conversation_summary = "\n".join([
        f"{msg.type}: {msg.content}" for msg in get_messages_history_from_immediate_graph_state(config)
    ])
    child_profile = state.get('child_profile', '')
    analysis_message = HumanMessage(
        content=f"Child profile: {child_profile}\n\n"
                f"Conversation: {conversation_summary}. "
    )

    response = llm.invoke([system_message, analysis_message])
    logger.info(f"speechGrammarWorker: Analysis completed with length: {len(response.content)}")
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
        content=f"Child profile: {child_profile}\n\n"
                f"Conversation: {conversation_summary}. "
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
        content=f"Child profile: {child_profile}\n\n"
                f"Conversation: {conversation_summary}"
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
        content=f"Child profile: {child_profile}\n\n"
                f"Conversation: {conversation_summary}."
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
        content=f"Child profile: {child_profile}\n\n"
                f"Conversation: {conversation_summary}"
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
    logger.info("foerderfokusWorker: Starting overall educational value analysis")
    system_message = SystemMessage(content=getFoerderfokusWorker_prompt())

    # Analyze the conversation without participating in it
    conversation_summary = "\n".join([
        f"{msg.type}: {msg.content}" for msg in get_messages_history_from_immediate_graph_state(config)
    ])
    child_profile = state.get('child_profile', '')
    grammar_analysis = state.get('grammar_analysis', '')
    speech_comprehension_analysis = state.get('speech_comprehension_analysis', '')
    sprachhandlung_analysis = state.get('sprachhandlung_analysis', '')
    vocabulary_analysis = state.get('vocabulary_analysis', '')
    boredom_analysis = state.get('boredom_analysis', '')
    analysis_message = HumanMessage(

        content=f"Child profile:\n{child_profile}.\n\n"
                f"Grammar analysis:\n{grammar_analysis}.\n\n"
                f"Speech comprehension analysis:\n{speech_comprehension_analysis}.\n\n"
                f"Sprachhandlung analysis:\n{sprachhandlung_analysis}.\n\n"
                f"Vocabulary analysis:\n{vocabulary_analysis}.\n\n"
                f"Boredom analysis:\n{boredom_analysis}.\n\n"
                f"Conversation:\n{conversation_summary}."
    )

    response = llm.invoke([system_message, analysis_message])
    logger.info(f"foerderfokusWorker: Analysis completed - {response.content[:100]}...")
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
    logger.info("aufgabenWorker: Starting task suggestions generation")
    system_message = SystemMessage(content=getAufgabenWorker_prompt())

    # Analyze the conversation without participating in it
    conversation_summary = "\n".join([
        f"{msg.type}: {msg.content}" for msg in get_messages_history_from_immediate_graph_state(config)
    ])
    child_profile = state.get('child_profile', '')
    foerderfokus = state.get('foerderfokus', '')
    analysis_message = HumanMessage(
        content=f"Förderfokus analysis:\n{foerderfokus}\n\n"
                f"Child profile:\n{child_profile}\n\n"
                f" Conversation:\n{conversation_summary}. "
    )

    response = llm.invoke([system_message, analysis_message])
    logger.info(f"aufgabenWorker: Task suggestions generated - {response.content[:100]}...")
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
        content=f"Child profile: {child_profile}\n\n"
                f"Conversation: {conversation_summary}"
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
    logger.info("satzbauBegrenzungsWorker: Starting sentence structure constraints generation")
    system_message = SystemMessage(content=getSatzbauBegrenzungsWorker_prompt())

    satzbau_analyse = state.get('satzbau_analysis', '')
    analysis_message = HumanMessage(
        content=f"Satzbauanalyse: {satzbau_analyse}"
    )

    response = llm.invoke([system_message, analysis_message])
    logger.info(f"satzbauBegrenzungsWorker: Constraints generated - {response.content[:100]}...")
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
    return ["speechGrammarWorker", "speechComprehensionWorker", "sprachhandlungsAnalyseWorker",
            "speechVocabularyWorker",
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


def load_beat_context(state: State) -> dict:
    """
    Load relevant beats from the beatpack based on conversation status.

    Strategy:
    - If tasks are planned (num_planned_tasks), distribute beats chronologically
    - Otherwise, use retrieval based on the last user message
    - For first interaction, use first few beats

    :param state: Current state
    :return: Updated state with beat_context and active_beat_ids
    """
    global beat_manager

    # Check if beat system is configured
    story_id = state.get("story_id")
    chapter_id = state.get("chapter_id")

    if not story_id or not chapter_id:
        logger.info("load_beat_context: No story_id/chapter_id configured, skipping beat loading")
        return {}

    if beat_manager is None:
        logger.warning("load_beat_context: Beat manager not initialized")
        return {}

    # Get beatpack retriever
    retriever = beat_manager.get_retriever(story_id, chapter_id)
    if retriever is None:
        logger.warning(f"load_beat_context: No beatpack found for {story_id}/{chapter_id}")
        return {}

    # Determine which beats to load
    num_planned_tasks = state.get("num_planned_tasks", 5)
    messages = state.get("messages", [])

    # Count user messages to determine interaction position
    user_message_count = sum(1 for msg in messages if isinstance(msg, HumanMessage))

    if user_message_count == 0:
        # First interaction - use chronologically distributed beats for tasks
        logger.info(f"load_beat_context: First interaction, loading {num_planned_tasks} distributed beats")
        beats = retriever.get_beats_for_tasks(num_planned_tasks)
    else:
        # Subsequent interactions - retrieve relevant beats based on last message
        last_user_message = None
        for msg in reversed(messages):
            if isinstance(msg, HumanMessage):
                last_user_message = msg.content
                break

        query = last_user_message if last_user_message else ""
        logger.info(f"load_beat_context: Retrieving beats for query: {query[:50]}...")

        # Retrieve top-k relevant beats
        top_k = min(num_planned_tasks, 6)  # Limit context size
        beats = retriever.retrieve_beats(query, top_k=top_k)

    # Format beats as context
    beat_context = retriever.format_beats_for_context(beats, include_entities=True)
    active_beat_ids = [beat.beat_id for beat in beats]

    logger.info(f"load_beat_context: Loaded {len(beats)} beats: {active_beat_ids}")

    return {
        "beat_context": beat_context,
        "active_beat_ids": active_beat_ids
    }


