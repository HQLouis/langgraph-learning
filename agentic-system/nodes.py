"""
Node functions for the Lingolino graphs.
"""
import logging
import os
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
from output_contract_builder import build_output_contract
from german_grammar_postprocess import correct_common_german_errors
from typing import Any, Optional
from config.conversation_termination_policy import get_termination_prompt, is_normal_phase, is_soft_termination_phase, \
    is_conversation_ended
from beats import BeatPackManager, BeatRetriever

# Initialize logger
logger = logging.getLogger(__name__)

# Verbose worker logging — set VERBOSE_WORKER_LOGGING=1 to enable detailed
# per-worker input/output logs.  Defaults to off for production.
VERBOSE_WORKER_LOGGING = os.getenv("VERBOSE_WORKER_LOGGING", "0").strip().lower() in ("1", "true", "yes")

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

def _detect_repetitive_starters(messages: list, window: int = 5) -> str | None:
    """
    Scan the last *window* AI messages for a repeated first-word pattern.
    Returns a German-language nudge to inject into the prompt, or None.
    """
    ai_msgs = [m for m in messages if isinstance(m, AIMessage)]
    recent = ai_msgs[-window:] if len(ai_msgs) >= window else ai_msgs
    if len(recent) < 3:
        return None

    first_words = [m.content.strip().split()[0] if m.content.strip() else "" for m in recent]
    from collections import Counter
    counts = Counter(first_words)
    most_common_word, most_common_count = counts.most_common(1)[0]

    # If ≥60 % of recent messages start with the same word → inject nudge
    if most_common_count / len(recent) >= 0.6:
        return (
            f'[ACHTUNG — SATZANFANG-WIEDERHOLUNG ERKANNT]\n'
            f'Deine letzten {len(recent)} Antworten begannen überwiegend mit "{most_common_word}".\n'
            f'Beginne diese Antwort ZWINGEND mit einem ANDEREN Wort. '
            f'Nutze z.B.: "Genau!", "Stimmt!", "Richtig!", "Ah!", "Super!", '
            f'"Hmm...", "Weißt du noch...", "Schau mal..." oder einen anderen natürlichen Einstieg.'
        )
    return None


def _detect_repeated_disengagement(messages: list, window: int = 5) -> str | None:
    """
    Scan the last *window* HumanMessage instances for disengagement signals.
    Returns a German nudge if ≥3 of the last window messages match, or None.
    """
    disengagement_keywords = {
        "nein", "nee", "ne", "nö", "weiß nicht", "weiss nicht",
        "keine ahnung", "will nicht", "mag nicht", "kein bock",
        "langweilig", "keine lust",
    }

    human_msgs = [m for m in messages if isinstance(m, HumanMessage)]
    recent = human_msgs[-window:] if len(human_msgs) >= window else human_msgs
    if len(recent) < 3:
        return None

    disengage_count = 0
    for msg in recent:
        text = msg.content.strip().lower()
        if any(kw in text for kw in disengagement_keywords):
            disengage_count += 1

    if disengage_count < 3:
        return None

    return (
        '[ACHTUNG — WIEDERHOLTES DESINTERESSE ERKANNT (REGEL 4B)]\n'
        'Das Kind hat mehrfach hintereinander Desinteresse oder Ablehnung signalisiert '
        '("nein", "weiß nicht", etc.).\n'
        'PFLICHT:\n'
        '1. Zeige Verständnis für das Desinteresse (z.B. "Kein Problem!", "Das ist okay!").\n'
        '2. STRENG VERBOTEN: Weitere Fragen oder Inhalte zur Geschichte! '
        'Erzähle NICHT weiter, frage NICHT nach Figuren, Szenen oder Handlungen!\n'
        '3. Biete stattdessen eine KOMPLETT ANDERE Aktivität an, z.B.: '
        '"Sollen wir lieber ein Ratespiel machen?", '
        '"Möchtest du lieber etwas malen?", '
        '"Was würdest du gerne machen?".\n'
        'AUSNAHME: Wenn die Geschichte bereits weitgehend durchgesprochen wurde '
        '→ verabschiede dich warmherzig statt eine Aktivität anzubieten.'
    )


def _check_story_near_end(
    covered_beat_ids: list,
    active_beat_ids: list,
    all_beats: list,
) -> bool:
    """Detect if conversation has reached final ~20% of the story."""
    total = len(all_beats)
    if total == 0:
        return False
    final_threshold = max(1, int(total * 0.2))  # last 20% of beats
    final_beat_ids = {b.beat_id for b in all_beats if b.order > total - final_threshold}
    covered_or_active = set(covered_beat_ids or []) | set(active_beat_ids or [])
    return bool(covered_or_active & final_beat_ids)


def _detect_story_end(messages: list, state: dict) -> str | None:
    """
    Detect if the story has reached its end. Uses beat-based progress tracking
    when available (primary), falling back to keyword matching (legacy).

    Respects REGEL 10: if the child's last message contains an emotion word,
    do NOT fire — let emotion exploration take precedence.
    """
    # Check REGEL 10 exclusion first: emotion words in child's last message
    emotion_words = {"lacht", "lachen", "traurig", "lustig", "fröhlich", "wütend",
                     "ängstlich", "angst", "freude", "freut", "weint", "weinen",
                     "glücklich", "aufgeregt", "überrascht"}
    human_msgs = [m for m in messages if isinstance(m, HumanMessage)]
    if human_msgs:
        last_child_text = human_msgs[-1].content.strip().lower()
        if any(ew in last_child_text for ew in emotion_words):
            return None

    _WRAP_UP_NUDGE = (
        '[ACHTUNG — ENDE DER GESCHICHTE ERKANNT (REGEL 8 — ÜBERSCHREIBT REGEL 3 und REGEL 7)]\n'
        'Die Geschichte hat ihre letzte Szene erreicht.\n'
        'PFLICHT: Reagiere KURZ auf die Antwort des Kindes (bestätige oder korrigiere '
        'in einem Satz), dann verabschiede dich SOFORT warmherzig im SELBEN Atemzug. '
        'Sage z.B.: "Das war eine tolle Geschichte! '
        'Bis zum nächsten Mal!"\n'
        'WICHTIG: Stelle KEINE Rückfrage nach der Korrektur — kein "Erinnerst du dich?", '
        'kein "Verstehst du?", kein "Alles klar?". '
        'REGEL 3 und REGEL 7 (Verständnisfrage nach Korrektur) gelten hier NICHT.\n'
        'STRENG VERBOTEN: Neue Fragen stellen, neue Themen einführen, '
        '"Soll ich dir verraten...?" anbieten, oder die Unterhaltung verlängern.'
    )

    # Primary: beat-based story-end detection
    story_near_end = state.get('story_near_end')
    if story_near_end is True:
        logger.info("_detect_story_end: Beat-based detection triggered (story_near_end=True)")
        return _WRAP_UP_NUDGE

    # Fallback: keyword-based detection (when beat system is not active)
    if story_near_end is None:
        logger.debug("_detect_story_end: No beat system active, using keyword fallback")
        story_end_keywords = {
            "eingeschlafen", "schläft ein", "schlief ein",
            "kichern", "glucksen", "lautes lachen", "lachten",
            "augen fielen zu", "fest geschlafen",
            "am ende", "zum ende", "ende der geschichte",
            "hast du das bild gemalt",
        }
        ai_msgs = [m for m in messages if isinstance(m, AIMessage)]
        recent_ai = ai_msgs[-8:] if len(ai_msgs) >= 8 else ai_msgs

        story_ended = any(
            any(kw in m.content.lower() for kw in story_end_keywords)
            for m in recent_ai
        )

        if story_ended:
            return _WRAP_UP_NUDGE

    return None


def _detect_repeated_errors(messages: list, window: int = 8) -> str | None:
    """
    Scan recent AIMessage instances for correction markers indicating the child
    has answered incorrectly multiple times. Fires if ≥3 corrections found.
    Returns a nudge to offer retelling, or None.
    """
    correction_markers = {
        "nicht ganz", "stimmt nicht", "das war es nicht", "im buch",
        "in der geschichte", "das ist nicht richtig", "fast richtig",
        "nicht genau", "versuchen wir es anders", "das stimmt so nicht",
        "nochmal überlegen",
    }

    ai_msgs = [m for m in messages if isinstance(m, AIMessage)]
    recent_ai = ai_msgs[-window:] if len(ai_msgs) >= window else ai_msgs

    correction_count = 0
    for msg in recent_ai:
        text = msg.content.lower()
        if any(marker in text for marker in correction_markers):
            correction_count += 1

    if correction_count < 3:
        return None

    return (
        '[ACHTUNG — WIEDERHOLTE FEHLER ERKANNT (REGEL 9B)]\n'
        'Das Kind hat mehrfach falsch geantwortet (≥3 Korrekturen erkannt).\n'
        'Stelle KEINE weitere Detailfrage. Biete stattdessen an, den relevanten '
        'Teil der Geschichte nochmal zu erzählen. Sage z.B.: "Soll ich dir den Teil '
        'nochmal erzählen?" — Sei ermutigend und geduldig, NICHT korrigierend.'
    )


def _detect_missing_transition_recap(messages: list, threshold: int = 24) -> str | None:
    """
    In long conversations (≥threshold messages), the in-context pattern of
    short Q&A exchanges can override REGEL 6's recap requirement.
    Inject a reminder when the conversation is long and recent AI messages
    lack transitional bridging phrases.
    """
    if len(messages) < threshold:
        return None

    bridging_phrases = {"danach", "und dann", "als nächstes", "nachdem",
                        "weißt du, was als nächstes", "vorher", "inzwischen",
                        "später", "davor"}
    ai_msgs = [m for m in messages if isinstance(m, AIMessage)]
    recent_ai = ai_msgs[-5:] if len(ai_msgs) >= 5 else ai_msgs

    # If recent AI messages already use bridging language, no nudge needed
    bridging_count = sum(
        1 for m in recent_ai
        if any(bp in m.content.lower() for bp in bridging_phrases)
    )
    if bridging_count >= 2:
        return None

    return (
        '[ERINNERUNG — REGEL 6: SZENENÜBERGANG MIT KURZER ZUSAMMENFASSUNG]\n'
        'Das Gespräch hat viele Austausche. Wenn du jetzt zu einem neuen Thema '
        'oder einer neuen Szene wechselst, fasse ZUERST kurz zusammen, was gerade '
        'passiert ist (1 Satz), BEVOR du die nächste Frage stellst. '
        'Verwende verbindende Sprache wie "Danach...", "Und dann...", '
        '"Nachdem Pia die Eier gefangen hat..." usw.'
    )


def masterChatbot(state: State, llm):
    """
    Main chatbot node that generates responses to the child.
    Now automatically constructs output contract from the response and context.

    :param state: Current state with messages and analysis
    :param llm: Language model instance
    :return: Updated state with new message and response_contract
    """
    logger.info("masterChatbot: Starting to generate response")
    is_first_message = not any(isinstance(msg, AIMessage) for msg in state["messages"])

    message_count = len(state["messages"]) // 2  # Assuming each interaction has a user and bot message
    logger.info(f"masterChatbot: Processing message count: {message_count}, is_first_message: {is_first_message}")

    # Build system context — master prompt is ALWAYS included so conversation
    # rules (clarity, empathy, verification, etc.) remain active even during
    # termination phases.  Termination guidance is layered on top separately.
    system_context = f"""
    {getMasterPrompt()}
    """

    # Inject child profile so the LLM knows the child's name, age, and gender
    child_profile = state.get('child_profile', '')
    if child_profile:
        system_context += f"""

    [KIND-PROFIL — IMMER BEACHTEN]
    {child_profile}
    Sprich das Kind immer mit seinem Namen an und verwende eine dem Geschlecht entsprechende Sprache.
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
    - Bei einem Themenwechsel oder Szenenübergang: Stelle ZUERST ausreichend Kontext her
      (REGEL 6: kurze Zusammenfassung + konkrete Namen), BEVOR du die Aufgabenform anwendest.
    """)

    aufgaben_val = state.get('aufgaben', '')
    satzbaubegrenzung_val = state.get('satzbaubegrenzung', '')
    if VERBOSE_WORKER_LOGGING:
        logger.info(
            f"masterChatbot: Received from background graph — "
            f"aufgaben: {len(aufgaben_val)} chars (empty: {not aufgaben_val.strip() if aufgaben_val else True}), "
            f"satzbaubegrenzung: {len(satzbaubegrenzung_val)} chars (empty: {not satzbaubegrenzung_val.strip() if satzbaubegrenzung_val else True})"
        )

    messages = [system_message]
    if is_normal_phase(message_count) and (aufgaben_val or satzbaubegrenzung_val):
        messages.append(meta_system)
        if VERBOSE_WORKER_LOGGING:
            logger.info(f"masterChatbot: Injected meta_system message with aufgaben and satzbaubegrenzung")
    else:
        if VERBOSE_WORKER_LOGGING:
            logger.info(f"masterChatbot: No meta_system injected (normal_phase: {is_normal_phase(message_count)}, has_aufgaben: {bool(aufgaben_val)}, has_satzbaubegrenzung: {bool(satzbaubegrenzung_val)})")
    if not is_normal_phase(message_count):
        termination_prompt = get_termination_prompt(message_count)
        termination_system = SystemMessage(content=f"""
        [GESPRÄCHSBEENDIGUNGSRICHTLINIEN — NICHT AN DAS KIND ADRESSIEREN]
        
        {termination_prompt}
        """)
        messages.append(termination_system)
        logger.info(f"masterChatbot: Added termination prompt for message count: {message_count}")

    messages += state["messages"]

    # Detect repetitive sentence starters and inject a targeted nudge
    starter_nudge = _detect_repetitive_starters(state["messages"])
    if starter_nudge:
        messages.append(SystemMessage(content=starter_nudge))
        logger.info("masterChatbot: Injected repetitive-starter nudge")

    # Detect story end FIRST — if story is ending, skip disengagement nudge
    # (story-end nudge already handles wrap-up; disengagement nudge would
    # conflict by offering activities instead of goodbye)
    story_end_nudge = _detect_story_end(state["messages"], state)
    if story_end_nudge:
        messages.append(SystemMessage(content=story_end_nudge))
        logger.info("masterChatbot: Injected story-end nudge")
    else:
        # Detect repeated disengagement only when story is NOT ending
        disengagement_nudge = _detect_repeated_disengagement(state["messages"])
        if disengagement_nudge:
            messages.append(SystemMessage(content=disengagement_nudge))
            logger.info("masterChatbot: Injected disengagement nudge")

    # Detect repeated errors and inject nudge
    error_nudge = _detect_repeated_errors(state["messages"])
    if error_nudge:
        messages.append(SystemMessage(content=error_nudge))
        logger.info("masterChatbot: Injected repeated-errors nudge")

    # Detect long conversation needing transition recaps
    recap_nudge = _detect_missing_transition_recap(state["messages"])
    if recap_nudge:
        messages.append(SystemMessage(content=recap_nudge))
        logger.info("masterChatbot: Injected transition-recap nudge")

    # Get natural language response (no JSON formatting)
    logger.info("masterChatbot: Starting LLM invocation for natural response")
    response = llm.invoke(messages)
    spoken_text = response.content.strip()

    # Apply grammar post-processing before output contract
    spoken_text, grammar_corrections = correct_common_german_errors(spoken_text)
    if grammar_corrections:
        logger.info(f"masterChatbot: Grammar corrections applied: {grammar_corrections}")

    logger.info(f"masterChatbot: Generated response with length: {len(spoken_text)}")

    # Get last user message for context
    last_user_message = None
    for msg in reversed(state["messages"]):
        if isinstance(msg, HumanMessage):
            last_user_message = msg.content
            break

    # Build output contract programmatically from the response and context
    logger.info("masterChatbot: Building output contract from context")

    # Get active beats if available
    active_beats = None
    if beat_manager and state.get('story_id') and state.get('chapter_id'):
        retriever = beat_manager.get_retriever(state['story_id'], state['chapter_id'])
        if retriever and state.get('active_beat_ids'):
            active_beats = [
                beat for beat in retriever.get_all_beats()
                if beat.beat_id in state['active_beat_ids']
            ]
            logger.info(f"masterChatbot: Using {len(active_beats)} active beats for contract building")

    logger.info(f"masterChatbot: Detected active beats: {[beat.beat_id for beat in active_beats]}") if active_beats else logger.info("masterChatbot: No active beats detected")
    response_contract = build_output_contract(
        response=spoken_text,
        active_beats=active_beats,
        story_id=state.get('story_id'),
        chapter_id=state.get('chapter_id'),
        aufgaben=state.get('aufgaben'),
        last_user_message=last_user_message
    )

    logger.info(f"masterChatbot: Built contract with {len(response_contract.grounding.evidence)} evidence items")

    # Grounding quality observability
    if active_beats and response_contract.grounding:
        claims = response_contract.grounding.claims if response_contract.grounding.claims else []
        logger.info(f"masterChatbot: Grounding: {len(claims)} claims from {len(active_beats)} beats")

    # Return both the spoken text as message and the full contract in state
    return {
        "messages": [AIMessage(content=spoken_text)],
        "response_contract": response_contract
    }


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
    prompt_content = getSpeechGrammarWorker_prompt()
    system_message = SystemMessage(content=prompt_content)
    if VERBOSE_WORKER_LOGGING:
        logger.info(f"speechGrammarWorker: Prompt length: {len(prompt_content)} chars (empty: {not prompt_content.strip()})")

    # Analyze the conversation without participating in it
    messages_history = get_messages_history_from_immediate_graph_state(config)
    conversation_summary = "\n".join([
        f"{msg.type}: {msg.content}" for msg in messages_history
    ])
    child_profile = state.get('child_profile', '')
    if VERBOSE_WORKER_LOGGING:
        logger.info(f"speechGrammarWorker: Input — {len(messages_history)} messages, child_profile: '{child_profile[:60]}...' " if child_profile else "speechGrammarWorker: Input — no child_profile")
    analysis_message = HumanMessage(
        content=f"Child profile: {child_profile}\n\n"
                f"Conversation: {conversation_summary}. "
    )

    response = llm.invoke([system_message, analysis_message])
    if VERBOSE_WORKER_LOGGING:
        logger.info(f"speechGrammarWorker: Output → grammar_analysis ({len(response.content)} chars): {response.content[:200]}...")
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
    logger.info("speechComprehensionWorker: Starting comprehension analysis")
    prompt_content = getSpeechComprehensionWorker_prompt()
    system_message = SystemMessage(content=prompt_content)
    if VERBOSE_WORKER_LOGGING:
        logger.info(f"speechComprehensionWorker: Prompt length: {len(prompt_content)} chars (empty: {not prompt_content.strip()})")

    # Analyze the conversation without participating in it
    messages_history = get_messages_history_from_immediate_graph_state(config)
    conversation_summary = "\n".join([
        f"{msg.type}: {msg.content}" for msg in messages_history
    ])
    child_profile = state.get('child_profile', '')
    if VERBOSE_WORKER_LOGGING:
        logger.info(f"speechComprehensionWorker: Input — {len(messages_history)} messages, child_profile: '{child_profile[:60]}...'" if child_profile else "speechComprehensionWorker: Input — no child_profile")
    analysis_message = HumanMessage(
        content=f"Child profile: {child_profile}\n\n"
                f"Conversation: {conversation_summary}. "
    )

    response = llm.invoke([system_message, analysis_message])
    if VERBOSE_WORKER_LOGGING:
        logger.info(f"speechComprehensionWorker: Output → speech_comprehension_analysis ({len(response.content)} chars): {response.content[:200]}...")
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
    logger.info("sprachhandlungsAnalyseWorker: Starting interaction analysis")
    prompt_content = getSprachhandlungAnalyseWorker_prompt()
    system_message = SystemMessage(content=prompt_content)
    if VERBOSE_WORKER_LOGGING:
        logger.info(f"sprachhandlungsAnalyseWorker: Prompt length: {len(prompt_content)} chars (empty: {not prompt_content.strip()})")

    # Analyze the conversation without participating in it
    messages_history = get_messages_history_from_immediate_graph_state(config)
    conversation_summary = "\n".join([
        f"{msg.type}: {msg.content}" for msg in messages_history
    ])
    child_profile = state.get('child_profile', '')
    if VERBOSE_WORKER_LOGGING:
        logger.info(f"sprachhandlungsAnalyseWorker: Input — {len(messages_history)} messages, child_profile: '{child_profile[:60]}...'" if child_profile else "sprachhandlungsAnalyseWorker: Input — no child_profile")
    analysis_message = HumanMessage(
        content=f"Child profile: {child_profile}\n\n"
                f"Conversation: {conversation_summary}"
    )

    response = llm.invoke([system_message, analysis_message])
    if VERBOSE_WORKER_LOGGING:
        logger.info(f"sprachhandlungsAnalyseWorker: Output → sprachhandlung_analysis ({len(response.content)} chars): {response.content[:200]}...")
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
    logger.info("speechVocabularyWorker: Starting vocabulary analysis")
    prompt_content = getSpeechVocabularyWorker_prompt()
    system_message = SystemMessage(content=prompt_content)
    if VERBOSE_WORKER_LOGGING:
        logger.info(f"speechVocabularyWorker: Prompt length: {len(prompt_content)} chars (empty: {not prompt_content.strip()})")

    # Analyze the conversation without participating in it
    messages_history = get_messages_history_from_immediate_graph_state(config)
    conversation_summary = "\n".join([
        f"{msg.type}: {msg.content}" for msg in messages_history
    ])
    child_profile = state.get('child_profile', '')
    if VERBOSE_WORKER_LOGGING:
        logger.info(f"speechVocabularyWorker: Input — {len(messages_history)} messages, child_profile: '{child_profile[:60]}...'" if child_profile else "speechVocabularyWorker: Input — no child_profile")
    analysis_message = HumanMessage(
        content=f"Child profile: {child_profile}\n\n"
                f"Conversation: {conversation_summary}."
    )

    response = llm.invoke([system_message, analysis_message])
    if VERBOSE_WORKER_LOGGING:
        logger.info(f"speechVocabularyWorker: Output → vocabulary_analysis ({len(response.content)} chars): {response.content[:200]}...")
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
    logger.info("boredomWorker: Starting boredom analysis")
    prompt_content = getBoredomWorker_prompt()
    system_message = SystemMessage(content=prompt_content)
    if VERBOSE_WORKER_LOGGING:
        logger.info(f"boredomWorker: Prompt length: {len(prompt_content)} chars (empty: {not prompt_content.strip()})")

    # Analyze the conversation without participating in it
    messages_history = get_messages_history_from_immediate_graph_state(config)
    conversation_summary = "\n".join([
        f"{msg.type}: {msg.content}" for msg in messages_history
    ])
    child_profile = state.get('child_profile', '')
    if VERBOSE_WORKER_LOGGING:
        logger.info(f"boredomWorker: Input — {len(messages_history)} messages, child_profile: '{child_profile[:60]}...'" if child_profile else "boredomWorker: Input — no child_profile")
    analysis_message = HumanMessage(
        content=f"Child profile: {child_profile}\n\n"
                f"Conversation: {conversation_summary}"
    )

    response = llm.invoke([system_message, analysis_message])
    if VERBOSE_WORKER_LOGGING:
        logger.info(f"boredomWorker: Output → boredom_analysis ({len(response.content)} chars): {response.content[:200]}...")
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
    prompt_content = getFoerderfokusWorker_prompt()
    system_message = SystemMessage(content=prompt_content)
    if VERBOSE_WORKER_LOGGING:
        logger.info(f"foerderfokusWorker: Prompt length: {len(prompt_content)} chars (empty: {not prompt_content.strip()})")

    # Analyze the conversation without participating in it
    messages_history = get_messages_history_from_immediate_graph_state(config)
    conversation_summary = "\n".join([
        f"{msg.type}: {msg.content}" for msg in messages_history
    ])
    child_profile = state.get('child_profile', '')
    grammar_analysis = state.get('grammar_analysis', '')
    speech_comprehension_analysis = state.get('speech_comprehension_analysis', '')
    sprachhandlung_analysis = state.get('sprachhandlung_analysis', '')
    vocabulary_analysis = state.get('vocabulary_analysis', '')
    boredom_analysis = state.get('boredom_analysis', '')
    if VERBOSE_WORKER_LOGGING:
        logger.info(
            f"foerderfokusWorker: Input analyses — "
            f"grammar: {len(grammar_analysis)} chars (empty: {not grammar_analysis.strip()}), "
            f"comprehension: {len(speech_comprehension_analysis)} chars (empty: {not speech_comprehension_analysis.strip()}), "
            f"sprachhandlung: {len(sprachhandlung_analysis)} chars (empty: {not sprachhandlung_analysis.strip()}), "
            f"vocabulary: {len(vocabulary_analysis)} chars (empty: {not vocabulary_analysis.strip()}), "
            f"boredom: {len(boredom_analysis)} chars (empty: {not boredom_analysis.strip()})"
        )
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
    if VERBOSE_WORKER_LOGGING:
        logger.info(f"foerderfokusWorker: Output → foerderfokus ({len(response.content)} chars): {response.content[:200]}...")
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
    prompt_content = getAufgabenWorker_prompt()
    system_message = SystemMessage(content=prompt_content)
    if VERBOSE_WORKER_LOGGING:
        logger.info(f"aufgabenWorker: Prompt length: {len(prompt_content)} chars (empty: {not prompt_content.strip()})")

    # Analyze the conversation without participating in it
    messages_history = get_messages_history_from_immediate_graph_state(config)
    conversation_summary = "\n".join([
        f"{msg.type}: {msg.content}" for msg in messages_history
    ])
    child_profile = state.get('child_profile', '')
    foerderfokus = state.get('foerderfokus', '')
    if VERBOSE_WORKER_LOGGING:
        logger.info(f"aufgabenWorker: Input — foerderfokus: {len(foerderfokus)} chars (empty: {not foerderfokus.strip()}), {len(messages_history)} messages")
    analysis_message = HumanMessage(
        content=f"Förderfokus analysis:\n{foerderfokus}\n\n"
                f"Child profile:\n{child_profile}\n\n"
                f" Conversation:\n{conversation_summary}. "
    )

    response = llm.invoke([system_message, analysis_message])
    if VERBOSE_WORKER_LOGGING:
        logger.info(f"aufgabenWorker: Output → aufgaben ({len(response.content)} chars): {response.content[:200]}...")
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
    logger.info("satzbauAnalyseWorker: Starting sentence structure analysis")
    prompt_content = getSatzbauAnalyseWorker_prompt()
    system_message = SystemMessage(content=prompt_content)
    if VERBOSE_WORKER_LOGGING:
        logger.info(f"satzbauAnalyseWorker: Prompt length: {len(prompt_content)} chars (empty: {not prompt_content.strip()})")

    # Analyze the conversation without participating in it
    messages_history = get_messages_history_from_immediate_graph_state(config)
    conversation_summary = "\n".join([
        f"{msg.type}: {msg.content}" for msg in messages_history
    ])
    child_profile = state.get('child_profile', '')
    if VERBOSE_WORKER_LOGGING:
        logger.info(f"satzbauAnalyseWorker: Input — {len(messages_history)} messages, child_profile: '{child_profile[:60]}...'" if child_profile else "satzbauAnalyseWorker: Input — no child_profile")
    analysis_message = HumanMessage(
        content=f"Child profile: {child_profile}\n\n"
                f"Conversation: {conversation_summary}"
    )

    response = llm.invoke([system_message, analysis_message])
    if VERBOSE_WORKER_LOGGING:
        logger.info(f"satzbauAnalyseWorker: Output → satzbau_analysis ({len(response.content)} chars): {response.content[:200]}...")
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
    prompt_content = getSatzbauBegrenzungsWorker_prompt()
    system_message = SystemMessage(content=prompt_content)
    if VERBOSE_WORKER_LOGGING:
        logger.info(f"satzbauBegrenzungsWorker: Prompt length: {len(prompt_content)} chars (empty: {not prompt_content.strip()})")

    satzbau_analyse = state.get('satzbau_analysis', '')
    if VERBOSE_WORKER_LOGGING:
        logger.info(f"satzbauBegrenzungsWorker: Input — satzbau_analysis: {len(satzbau_analyse)} chars (empty: {not satzbau_analyse.strip()})")
    analysis_message = HumanMessage(
        content=f"Satzbauanalyse: {satzbau_analyse}"
    )

    response = llm.invoke([system_message, analysis_message])
    if VERBOSE_WORKER_LOGGING:
        logger.info(f"satzbauBegrenzungsWorker: Output → satzbaubegrenzung ({len(response.content)} chars): {response.content[:200]}...")
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
    logger.info("load_analysis: Reading analysis results from background graph")
    bg_thread_id = config["configurable"]["thread_id"] + "_analysis"
    snapshot = background_graph_instance.get_state({
        "configurable": {"thread_id": bg_thread_id}
    })
    aufgaben = snapshot.values.get("aufgaben", "")
    satzbaubegrenzung = snapshot.values.get("satzbaubegrenzung", "")
    if VERBOSE_WORKER_LOGGING:
        logger.info(
            f"load_analysis: Read from background state — "
            f"aufgaben: {len(aufgaben)} chars (empty: {not aufgaben.strip()}), "
            f"satzbaubegrenzung: {len(satzbaubegrenzung)} chars (empty: {not satzbaubegrenzung.strip()})"
        )
        if aufgaben.strip():
            logger.info(f"load_analysis: aufgaben preview: {aufgaben[:200]}...")
        if satzbaubegrenzung.strip():
            logger.info(f"load_analysis: satzbaubegrenzung preview: {satzbaubegrenzung[:200]}...")
    analyses = {
        "aufgaben": aufgaben,
        "satzbaubegrenzung": satzbaubegrenzung,
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

    # Beat progress tracking: accumulate covered beats and check story-near-end
    prev_covered = list(state.get("covered_beat_ids") or [])
    covered_beat_ids = list(set(prev_covered) | set(active_beat_ids))

    # Check if conversation has reached final beats
    all_beats = retriever.get_all_beats()
    story_near_end = _check_story_near_end(covered_beat_ids, active_beat_ids, all_beats)
    logger.info(f"load_beat_context: covered={len(covered_beat_ids)}/{len(all_beats)} beats, story_near_end={story_near_end}")

    return {
        "beat_context": beat_context,
        "active_beat_ids": active_beat_ids,
        "covered_beat_ids": covered_beat_ids,
        "story_near_end": story_near_end,
    }


