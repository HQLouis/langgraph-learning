"""
Conversation Termination Policy Configuration

This configuration defines thresholds and prompts for managing conversation termination.
The thresholds determine when the bot should start ending the conversation and when it must end.
"""

# Threshold definitions (in number of messages)
SOFT_TERMINATION_THRESHOLD = 15
"""
Soft termination threshold: Number of messages after which the bot should 
start slowly bringing the conversation to an end.
"""

HARD_TERMINATION_THRESHOLD = 20
"""
Hard termination threshold: Number of messages after which the bot must 
end the conversation and not start any new interactions.
"""

# Prompt texts for different conversation phases

NORMAL_PHASE_PROMPT = """
Lass das Gespräch nicht zu Ende gehen. Halte die Interaktion ansprechend und offen.
"""
"""
Prompt used during the normal phase of conversation (before soft threshold).
"""

SOFT_TERMINATION_PROMPT = """
Bringe das Gespräch langsam zu einem Ende. Beginne das aktuelle Thema abzuschließen und führe es zu einem natürlichen Abschluss, ohne abrupt zu sein.
"""
"""
Prompt used during soft termination phase (between soft and hard threshold).
"""

HARD_TERMINATION_PROMPT = """
Das Gespräch muss jetzt beendet werden.
WICHTIG: Reagiere ZUERST auf die letzte Antwort des Kindes (bestätige, kommentiere kurz).
Leite DANN freundlich zum Abschied über.
Beginne KEINE neue Interaktion und stelle KEINE neuen Fragen.
Verabschiede dich warmherzig.
"""
"""
Prompt used during hard termination phase (at or beyond hard threshold).
"""


def get_termination_prompt(message_count: int) -> str:
    """
    Get the appropriate termination prompt based on the current message count.

    :param message_count: Current number of messages in the conversation
    :return: Appropriate prompt text for the current phase
    """
    if message_count >= HARD_TERMINATION_THRESHOLD:
        return HARD_TERMINATION_PROMPT
    elif message_count >= SOFT_TERMINATION_THRESHOLD:
        return SOFT_TERMINATION_PROMPT
    else:
        return NORMAL_PHASE_PROMPT


def get_termination_phase(message_count: int) -> str:
    """
    Get the current termination phase based on message count.

    :param message_count: Current number of messages in the conversation
    :return: Phase name ('normal', 'soft_termination', or 'hard_termination')
    """
    if message_count >= HARD_TERMINATION_THRESHOLD:
        return 'hard_termination'
    elif message_count >= SOFT_TERMINATION_THRESHOLD:
        return 'soft_termination'
    else:
        return 'normal'

def is_conversation_ended(message_count: int) -> bool:
    """
    Determine if the conversation should be ended based on message count.

    :param message_count: Current number of messages in the conversation
    :return: True if conversation should be ended, False otherwise
    """
    return message_count >= HARD_TERMINATION_THRESHOLD

def is_soft_termination_phase(message_count: int) -> bool:
    """
    Determine if the conversation is in the soft termination phase.

    :param message_count: Current number of messages in the conversation
    :return: True if in soft termination phase, False otherwise
    """
    return SOFT_TERMINATION_THRESHOLD <= message_count < HARD_TERMINATION_THRESHOLD

def is_normal_phase(message_count: int) -> bool:
    """
    Determine if the conversation is in the normal phase.

    :param message_count: Current number of messages in the conversation
    :return: True if in normal phase, False otherwise
    """
    return message_count < SOFT_TERMINATION_THRESHOLD