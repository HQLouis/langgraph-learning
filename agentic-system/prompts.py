"""
Worker prompts for the agentic system.
This module now supports dynamic loading from AWS S3 with fallback to local prompts.
"""
from prompt_repository import get_prompt_repository
from local_fallback_prompts import (
    audio_book,
    child_profile,
    speechGrammarWorker_prompt,
    speech_comprehension_worker_prompt,
    sprachhandlung_analyse_worker_prompt,
    speechVocabularyWorker_prompt,
    boredomWorker_prompt,
    foerderfokusWorker_prompt,
    aufgabenWorker_prompt,
    satzbau_analyse_worker_prompt,
    satzbau_begrenzungs_worker_prompt,
    master_prompt
)



# ============================================================================
# REPOSITORY INITIALIZATION
# Register fallback prompts with the repository
# ============================================================================

_repository = get_prompt_repository()

# Register all fallback prompts
_repository.register_fallback('audio_book', lambda: audio_book)
_repository.register_fallback('child_profile', lambda: child_profile)
_repository.register_fallback('speech_grammar_worker', lambda: speechGrammarWorker_prompt)
_repository.register_fallback('speech_comprehension_worker', lambda: speech_comprehension_worker_prompt)
_repository.register_fallback('sprachhandlung_analyse_worker', lambda: sprachhandlung_analyse_worker_prompt)
_repository.register_fallback('speech_vocabulary_worker', lambda: speechVocabularyWorker_prompt)
_repository.register_fallback('boredom_worker', lambda: boredomWorker_prompt)
_repository.register_fallback('foerderfokus_worker', lambda: foerderfokusWorker_prompt)
_repository.register_fallback('aufgaben_worker', lambda: aufgabenWorker_prompt)
_repository.register_fallback('satzbau_analyse_worker', lambda: satzbau_analyse_worker_prompt)
_repository.register_fallback('satzbau_begrenzungs_worker', lambda: satzbau_begrenzungs_worker_prompt)
_repository.register_fallback('master', lambda: master_prompt)


# ============================================================================
# PUBLIC API - These functions now fetch from S3 or fall back to local
# ============================================================================

def getAudioBook() -> str:
    """
    Get the Audio Book prompt.
    Tries S3 first, falls back to local prompt if unavailable.

    :return: Prompt content
    """
    return _repository.get_prompt('audio_book')

def getChildProfile() -> str:
    """
    Get the Child Profile prompt.
    Tries S3 first, falls back to local prompt if unavailable.

    :return: Prompt content
    """
    return _repository.get_prompt('child_profile')

def getSpeechGrammarWorker_prompt() -> str:
    """
    Get the Speech Grammar Worker prompt.
    Tries S3 first, falls back to local prompt if unavailable.

    :return: Prompt content
    """
    return _repository.get_prompt('speech_grammar_worker')

def getSpeechComprehensionWorker_prompt() -> str:
    """
    Get the Speech Comprehension Worker prompt.
    Tries S3 first, falls back to local prompt if unavailable.

    :return: Prompt content
    """
    return _repository.get_prompt('speech_comprehension_worker')

def getSprachhandlungAnalyseWorker_prompt() -> str:
    """
    Get the Sprachhandlung Analyse Worker prompt.
    Tries S3 first, falls back to local prompt if unavailable.

    :return: Prompt content
    """
    return _repository.get_prompt('sprachhandlung_analyse_worker')

def getSpeechVocabularyWorker_prompt() -> str:
    """
    Get the Speech Vocabulary Worker prompt.
    Tries S3 first, falls back to local prompt if unavailable.

    :return: Prompt content
    """
    return _repository.get_prompt('speech_vocabulary_worker')

def getBoredomWorker_prompt() -> str:
    """
    Get the Boredom Worker prompt.
    Tries S3 first, falls back to local prompt if unavailable.

    :return: Prompt content
    """
    return _repository.get_prompt('boredom_worker')

def getFoerderfokusWorker_prompt() -> str:
    """
    Get the Foerderfokus Worker prompt.
    Tries S3 first, falls back to local prompt if unavailable.

    :return: Prompt content
    """
    return _repository.get_prompt('foerderfokus_worker')

def getAufgabenWorker_prompt() -> str:
    """
    Get the Aufgaben Worker prompt.
    Tries S3 first, falls back to local prompt if unavailable.

    :return: Prompt content
    """
    return _repository.get_prompt('aufgaben_worker')

def getSatzbauAnalyseWorker_prompt() -> str:
    """
    Get the Satzbau Analyse Worker prompt.
    Tries S3 first, falls back to local prompt if unavailable.

    :return: Prompt content
    """
    return _repository.get_prompt('satzbau_analyse_worker')

def getSatzbauBegrenzungsWorker_prompt() -> str:
    """
    Get the Satzbau Begrenzungs Worker prompt.
    Tries S3 first, falls back to local prompt if unavailable.

    :return: Prompt content
    """
    return _repository.get_prompt('satzbau_begrenzungs_worker')


def getMasterPrompt() -> str:
    """
    Get the Master Prompt for the main chatbot.
    Tries S3 first, falls back to local prompt if unavailable.

    :return: Prompt content
    """
    return _repository.get_prompt('master')
