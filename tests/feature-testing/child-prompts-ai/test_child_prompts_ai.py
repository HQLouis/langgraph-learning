"""
Feature: Child Prompts AI ("Kind fordert KI auf")
Test file: When a child asks the AI to do a task or help, the AI should
           engage helpfully — offer to do it together, ask what specifically
           the child needs help with, or recognize word-finding difficulty.

Three sub-behaviours are tested:
  1. Collaborative help: When the AI asks for a rhyme and the child deflects
     with "nein, und dir?", the AI should recognize the child wants help
     and offer to do it together.
  2. Give opinion / help when asked: When the child explicitly asks for help
     ("Kannst du mir helfen?"), the AI should respond helpfully and ask
     what specifically the child does not know.
  3. Word-finding support: When the child says "Ich weiss nicht wie das
     heisst..", the AI should recognize word-finding difficulty and offer
     to help explain the word.

Stories used:
  - "Bobos Adventskalender" (Example 1)
  - "Pia muss nicht perfekt sein" (Examples 2, 3)

Two strategies are tested:
  Strategy A — fixture-based (fast, reproducible)
  Strategy B — fully simulated (realistic, end-to-end)

Markers:
  llm_feature   — all tests here (real LLM involved)
  llm_judge     — LLM judge is called
  simulated     — Strategy B tests only
"""

import pytest
from langchain_core.messages import HumanMessage, AIMessage

from feature_testing_utils import (
    FIXTURE_BOBO_AUDIO_BOOK,
    FIXTURE_BOBO_CHAPTER_ID,
    FIXTURE_BOBO_STORY_ID,
    FIXTURE_PIA_AUDIO_BOOK,
    FIXTURE_PIA_STORY_ID,
    FIXTURE_PIA_CHAPTER_ID,
    build_state_with_beats,
    llm_judge,
    simulate_conversation,
    state_to_setting,
    simulation_to_setting,
)
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import ft_config as _cfg

# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _script_to_messages(script: list[str]) -> list:
    """
    Convert a child-first conversation script to a LangChain message list.

    Even indices (0, 2, 4, ...) -> HumanMessage (child).
    Odd  indices (1, 3, 5, ...) -> AIMessage (system).
    """
    messages = []
    for i, text in enumerate(script):
        if i % 2 == 0:
            messages.append(HumanMessage(content=text))
        else:
            messages.append(AIMessage(content=text))
    return messages


# ---------------------------------------------------------------------------
# Conversation scripts — child-first, odd-length
# ---------------------------------------------------------------------------

# Example 1 (BOBO): AI asks for a rhyme, child deflects with "nein, und dir?"
# The AI should recognize the child is asking the AI to do the task and
# offer to do it together or help.
SCRIPT_COLLABORATIVE_HELP = [
    # child
    'hallo',
    # system
    'Hallo! Ich bin Thilio, dein Sprachbegleiter.'
    ' Wir haben gerade die Geschichte von Bobo geh\u00f6rt,'
    ' der mit seinem Papa einen Adventskalender bastelt.'
    ' Wei\u00dft du noch, was Bobo und Papa als Erstes gemacht haben?',
    # child
    'aus dem fenster geschaut',
    # system
    'Ja, genau! Bobo und Papa haben aus dem K\u00fcchenfenster geschaut.'
    ' Dann kommt die Postbotin. Sie hat ein neues Fahrrad.'
    ' Bobo darf auf dem Fahrrad sitzen. Klingeling!'
    ' F\u00e4llt dir ein Reim zu "Klingeling" ein?',
    # child — TESTED: child deflects the rhyme task back to AI
    'nein, und dir?',
]

# Example 2 (PIA): Child explicitly asks for help
# AI should respond helpfully, ask what specifically the child does not know.
SCRIPT_GIVE_OPINION_WHEN_ASKED = [
    # child
    'hallo',
    # system
    'Hallo! Ich bin Thilio.'
    ' Wir haben gerade die Geschichte von Pia geh\u00f6rt,'
    ' die immer alles richtig macht.'
    ' Was hat Pia denn als Allererstes an diesem Freitag gemacht?',
    # child
    'socken angezogen',
    # system
    'Ja, Pia hat Socken angezogen, die zusammenpassen.'
    ' Pia hat auch ihrem Hamster Hubert Brokkoli gegeben.'
    ' Was denkst du, warum mag Hubert Brokkoli so gern?',
    # child — TESTED: child asks for help
    'Ich wei\u00df nicht. Kannst du mir helfen?',
]

# Example 3 (PIA): Child expresses word-finding difficulty
# AI should recognize word-finding difficulty and offer to help.
SCRIPT_WORD_FINDING_SUPPORT = [
    # child
    'hallo',
    # system
    'Hallo! Ich bin Thilio.'
    ' Wir haben gerade die Geschichte von Pia geh\u00f6rt.'
    ' Pia macht beim Talentwettbewerb mit.'
    ' Was jongliert Pia alles?',
    # child
    'hubert und den ballon',
    # system
    'Ja, Pia wirft Hubert und den Wasserballon in die Luft.'
    ' Und sie hat auch noch etwas anderes.'
    ' Wei\u00dft du, was das dritte Ding ist?',
    # child — TESTED: child has word-finding difficulty
    'Ich wei\u00df nicht wie das hei\u00dft..',
]


# ---------------------------------------------------------------------------
# Judge criteria (English)
# ---------------------------------------------------------------------------

CRITERION_COLLABORATIVE_HELP = (
    "The AI previously asked the child to come up with a rhyme for "
    "'Klingeling'. The child replied 'nein, und dir?' — meaning the child "
    "is asking the AI to do the task instead. Does the system response: "
    "(1) recognize that the child is asking the AI to help or do the task, AND "
    "(2) offer to do it together, help the child, or attempt the rhyme itself "
    "rather than ignoring the child's request or simply repeating the question? "
    "Return PASS if the system recognizes the child's request and engages "
    "helpfully (offers to try together, makes a rhyme, or asks if the child "
    "wants the AI to try), FAIL if it ignores the request, changes topic "
    "entirely, or just repeats the original question."
)

CRITERION_GIVE_OPINION_WHEN_ASKED = (
    "The child said 'Ich wei\u00df nicht. Kannst du mir helfen?' — explicitly "
    "asking the AI for help. Does the system response: "
    "(1) acknowledge the child's request for help, AND "
    "(2) respond helpfully — for example by giving a hint, asking what "
    "specifically the child does not know, offering an explanation, or "
    "providing a possible answer — RATHER than ignoring the request, "
    "just moving on, or repeating the same question? "
    "Return PASS if the system acknowledges the help request and responds "
    "helpfully, FAIL if it ignores the request or fails to offer assistance."
)

CRITERION_WORD_FINDING_SUPPORT = (
    "The child said 'Ich wei\u00df nicht wie das hei\u00dft..' — indicating "
    "word-finding difficulty. The child seems to know what the object is but "
    "cannot recall the word. Does the system response: "
    "(1) recognize the word-finding difficulty (the child knows the thing "
    "but not the word for it), AND "
    "(2) offer to help — for example by asking the child to describe it, "
    "giving a hint about the word, asking if the child means a specific "
    "object, or explaining what the word might be — RATHER than ignoring "
    "the difficulty or just telling the answer without acknowledgment? "
    "Return PASS if the system recognizes the word-finding struggle and "
    "offers supportive help, FAIL if it ignores the difficulty or simply "
    "moves on."
)


# ---------------------------------------------------------------------------
# Simulated child inputs for Strategy B — ODD length (ends with child)
# ---------------------------------------------------------------------------

SIMULATED_CHILD_ASKS_FOR_HELP = [
    'hallo',
    'Hallo! Ich bin Thilio. Wir haben die Geschichte von Pia geh\u00f6rt. '
    'Was hat Pia als Erstes am Freitag gemacht?',
    'socken',
    'Ja, Pia hat Socken angezogen. Pia hat auch Hubert gef\u00fcttert. '
    'Was denkst du, warum mag Hubert Brokkoli?',
    'Ich wei\u00df nicht. Kannst du mir helfen?',
]


# ---------------------------------------------------------------------------
# Strategy A — fixture-based tests
# ---------------------------------------------------------------------------

@pytest.mark.llm_feature
@pytest.mark.llm_judge
class TestChildPromptsAIFixtureBased:
    """Strategy A: Verify AI responds helpfully when child asks for help."""

    def test_collaborative_help_on_request(
        self, system_llm, judge_llm, n_runs, pass_threshold, run_details_recorder
    ):
        """
        Example 1 (BOBO): AI asks for a rhyme, child says 'nein, und dir?'
        AI should recognize the child is asking AI to do the task and offer
        to do it together or help.
        """
        state = build_state_with_beats(
            child_name="Emma",
            child_age=4,
            child_gender="weiblich",
            messages=_script_to_messages(SCRIPT_COLLABORATIVE_HELP),
            audio_book=FIXTURE_BOBO_AUDIO_BOOK,
            story_id=FIXTURE_BOBO_STORY_ID,
            chapter_id=FIXTURE_BOBO_CHAPTER_ID,
        )

        def _run() -> tuple[bool, str, str]:
            from nodes import masterChatbot
            result = masterChatbot(state, system_llm)
            spoken_text = result["messages"][-1].content
            return llm_judge(judge_llm, spoken_text, CRITERION_COLLABORATIVE_HELP)

        run_details_recorder(
            _run, n_runs, pass_threshold,
            setting=state_to_setting(state, CRITERION_COLLABORATIVE_HELP),
        )

    def test_give_opinion_when_asked(
        self, system_llm, judge_llm, n_runs, pass_threshold, run_details_recorder
    ):
        """
        Example 2 (PIA): Child says 'Ich weiss nicht. Kannst du mir helfen?'
        AI should respond helpfully and ask what specifically the child
        does not know.
        """
        state = build_state_with_beats(
            child_name="Emma",
            child_age=6,
            child_gender="weiblich",
            messages=_script_to_messages(SCRIPT_GIVE_OPINION_WHEN_ASKED),
            audio_book=FIXTURE_PIA_AUDIO_BOOK,
            story_id=FIXTURE_PIA_STORY_ID,
            chapter_id=FIXTURE_PIA_CHAPTER_ID,
        )

        def _run() -> tuple[bool, str, str]:
            from nodes import masterChatbot
            result = masterChatbot(state, system_llm)
            spoken_text = result["messages"][-1].content
            return llm_judge(judge_llm, spoken_text, CRITERION_GIVE_OPINION_WHEN_ASKED)

        run_details_recorder(
            _run, n_runs, pass_threshold,
            setting=state_to_setting(state, CRITERION_GIVE_OPINION_WHEN_ASKED),
        )

    def test_word_finding_support(
        self, system_llm, judge_llm, n_runs, pass_threshold, run_details_recorder
    ):
        """
        Example 3 (PIA): Child says 'Ich weiss nicht wie das heisst..'
        AI should recognize word-finding difficulty and offer to help
        explain the word.
        """
        state = build_state_with_beats(
            child_name="Emma",
            child_age=6,
            child_gender="weiblich",
            messages=_script_to_messages(SCRIPT_WORD_FINDING_SUPPORT),
            audio_book=FIXTURE_PIA_AUDIO_BOOK,
            story_id=FIXTURE_PIA_STORY_ID,
            chapter_id=FIXTURE_PIA_CHAPTER_ID,
        )

        def _run() -> tuple[bool, str, str]:
            from nodes import masterChatbot
            result = masterChatbot(state, system_llm)
            spoken_text = result["messages"][-1].content
            return llm_judge(judge_llm, spoken_text, CRITERION_WORD_FINDING_SUPPORT)

        run_details_recorder(
            _run, n_runs, pass_threshold,
            setting=state_to_setting(state, CRITERION_WORD_FINDING_SUPPORT),
        )


# ---------------------------------------------------------------------------
# Strategy B — fully-simulated tests
# ---------------------------------------------------------------------------

@pytest.mark.llm_feature
@pytest.mark.llm_judge
@pytest.mark.simulated
class TestChildPromptsAISimulated:
    """Strategy B: Full simulation where child asks AI for help."""

    def test_child_asks_for_help_simulated(
        self, system_llm, judge_llm, pass_threshold, run_details_recorder
    ):
        """
        Full simulation: child explicitly asks for help mid-conversation.
        The final system response should acknowledge the request and
        offer assistance.
        """
        n = _cfg.SIMULATED_N_RUNS

        def _run() -> tuple:
            final_state, spoken_text = simulate_conversation(
                system_llm_instance=system_llm,
                child_name="Emma",
                child_age=6,
                child_gender="weiblich",
                child_inputs=SIMULATED_CHILD_ASKS_FOR_HELP,
                audio_book=FIXTURE_PIA_AUDIO_BOOK,
                story_id=FIXTURE_PIA_STORY_ID,
                chapter_id=FIXTURE_PIA_CHAPTER_ID,
            )
            passed, resp, reason = llm_judge(
                judge_llm, spoken_text, CRITERION_GIVE_OPINION_WHEN_ASKED,
            )
            from langchain_core.messages import HumanMessage as _HM
            conversation = [
                {"role": "Child" if isinstance(m, _HM) else "System",
                 "content": m.content}
                for m in final_state.get("messages", [])
            ]
            return passed, resp, reason, conversation

        run_details_recorder(
            _run, n, pass_threshold,
            setting=simulation_to_setting(
                "Emma", 6, "weiblich",
                SIMULATED_CHILD_ASKS_FOR_HELP,
                CRITERION_GIVE_OPINION_WHEN_ASKED,
            ),
        )
