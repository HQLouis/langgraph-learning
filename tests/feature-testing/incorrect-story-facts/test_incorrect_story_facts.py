"""
Feature: Incorrect Story Facts
Test file: When child gives wrong story information, system should correct
           gently and without judgment.

The feature requires that when a child provides incorrect facts about the
story, the system:
  - Corrects the information gently (not critically or judgmentally)
  - May ask a small confirmation to check the child remembers
  - For short/simple corrections, gives the correct answer directly
  - Incorporates correct information neutrally

Stories used:
  - "Pia muss nicht perfekt sein" (Examples 1, 3)
  - "Bobos Adventskalender" (Example 2)

Two strategies are tested:
  Strategy A — fixture-based (fast, reproducible):
      State and conversation history are hardcoded.
      The LLM is called only once per N-run iteration.

  Strategy B — fully simulated (realistic, end-to-end):
      No state is pre-set.  The entire conversation is conducted using
      real LLMs from scratch with hardcoded child inputs.

Markers:
  llm_feature   — all tests here (real LLM involved)
  llm_judge     — LLM judge is called
  simulated     — Strategy B tests only
"""

import pytest
from langchain_core.messages import AIMessage, HumanMessage

from feature_testing_utils import (
    FIXTURE_BOBO_AUDIO_BOOK,
    FIXTURE_BOBO_CHAPTER_ID,
    FIXTURE_BOBO_STORY_ID,
    FIXTURE_PIA_AUDIO_BOOK,
    FIXTURE_PIA_CHAPTER_ID,
    FIXTURE_PIA_STORY_ID,
    build_state,
    llm_judge,
    simulate_conversation,
    state_to_setting,
    simulation_to_setting,
)

import ft_config as _cfg

# ---------------------------------------------------------------------------
# Helper — convert child-first script to LangChain message list
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
# Conversation scripts
# ---------------------------------------------------------------------------

# Example 1 (PIA): Child says "Lisa und sarah" for Pia's friends.
# Correct answer: Millie und Sarah.
# System should correct AND ask a small confirmation.
SCRIPT_WRONG_FRIEND_NAMES = [
    # child
    'Hallo!',
    # system
    'Hallo! Ich bin Thilio, dein Sprachbegleiter.'
    ' Wir haben gerade die Geschichte von Pia geh\u00f6rt.'
    ' Pia macht immer alles richtig!'
    ' Wei\u00dft du noch, was Pia morgens als Erstes gemacht hat?',
    # child
    'socken',
    # system
    'Ja, Pia hat Socken angezogen, die zusammenpassen.'
    ' Pia hat auch ihren Hamster Hubert gef\u00fcttert.'
    ' In der Schule war Pia mit ihren Freundinnen in einem Kochteam.'
    ' Wei\u00dft du, wie die Freundinnen hei\u00dfen?',
    # child — TESTED: wrong answer, system should correct gently + confirm
    'Lisa und sarah',
]

# Example 2 (BOBO): Child says "er sagt ja" when asked what Bobo does
# when Mama asks if he painted the picture.
# Correct: Bobo says nothing, he fell asleep.
# System should give correct answer directly, short, not critical.
SCRIPT_BOBO_WRONG_ANSWER = [
    # child
    'hallo',
    # system
    'Hallo! Ich bin Thilio, dein Sprachbegleiter.'
    ' Wir haben gerade die Geschichte von Bobo geh\u00f6rt,'
    ' der mit seinem Papa einen Adventskalender bastelt.'
    ' Wei\u00dft du, was Bobo und Papa als Erstes gemacht haben?',
    # child
    'aus dem fenster geschaut',
    # system
    'Ja, genau! Bobo und Papa schauen aus dem K\u00fcchenfenster.'
    ' Dann kommt die Postbotin. Sie bringt einen Zettel.'
    ' Papa und Bobo gehen zur Post und holen ein Paket.'
    ' Zu Hause basteln sie einen Adventskalender.'
    ' Bobo malt ein Haus auf die Pappe.'
    ' Dann kommt Mama nach Hause.'
    ' Mama fragt: "Hast du das Bild gemalt, Bobo?"'
    ' Was macht Bobo, als Mama das fragt?',
    # child — TESTED: wrong answer, system should correct directly + short
    'er sagt ja',
]

# Example 3 (PIA): Child says wrong food for Hubert.
# Correct: Brokkoli.
# System should incorporate correct info neutrally, not judgmentally.
SCRIPT_WRONG_HUBERT_FOOD = [
    # child
    'Hallo!',
    # system
    'Hallo! Ich bin Thilio, dein Sprachbegleiter.'
    ' Wir haben die Geschichte von Pia geh\u00f6rt.'
    ' Pia hat morgens viel gemacht.'
    ' Was hat Pia ihrem Hamster Hubert gegeben?',
    # child — TESTED: wrong answer, system should correct neutrally
    'Marmelade',
]


# ---------------------------------------------------------------------------
# Judge criteria (English)
# ---------------------------------------------------------------------------

CRITERION_GENTLE_CORRECTION_WITH_CONFIRMATION = (
    "The child said 'Lisa und Sarah' when asked about Pia's friends. "
    "The correct answer is 'Millie und Sarah'. Does the system response: "
    "(1) correct the wrong name gently (mention that the friends are called "
    "Millie und Sarah, not Lisa und Sarah), AND "
    "(2) include a small confirmation check — ask whether the child now "
    "remembers or understands (e.g. 'Erinnerst du dich?' or similar)? "
    "The system must NOT just move on immediately without checking. "
    "The correction must sound friendly and non-judgmental. "
    "Return PASS if the system corrects the name AND checks for confirmation, "
    "FAIL if it skips the correction, sounds critical, or moves on without "
    "any confirmation check."
)

CRITERION_SHORT_DIRECT_CORRECTION = (
    "The child said 'er sagt ja' when asked what Bobo does when Mama asks "
    "if he painted the picture. The correct answer is that Bobo does not "
    "answer because he fell asleep. Does the system response: "
    "(1) provide the correct answer (Bobo says nothing / Bobo fell asleep), AND "
    "(2) keep the correction short and direct — no lengthy commentary "
    "about the child's mistake? "
    "The response must NOT sound critical or judgmental toward the child. "
    "Return PASS if the system gives the correct answer directly without "
    "sounding critical, FAIL if it is overly long, critical, or fails to "
    "provide the correct information."
)

CRITERION_NEUTRAL_FACT_CORRECTION = (
    "The child said 'Marmelade' when asked what Pia gave her hamster Hubert. "
    "The correct answer is Brokkoli. Does the system response: "
    "(1) incorporate the correct information (Brokkoli) into the reply, AND "
    "(2) do so neutrally — without reacting correctively, judgmentally, "
    "or making the child feel bad about the wrong answer? "
    "The tone should be warm and matter-of-fact, as if simply sharing "
    "the story fact. "
    "Return PASS if the system mentions Brokkoli in a neutral, "
    "non-judgmental way, FAIL if it sounds corrective, critical, "
    "or fails to mention the correct food."
)


# ---------------------------------------------------------------------------
# Simulated child inputs for Strategy B
# ---------------------------------------------------------------------------

# Child gives a wrong answer about Hubert's food during normal conversation.
# ODD length (3 elements) — ends with child utterance.
# Matches spec Example 3: AI asks about Hubert's food, child says wrong answer.
SIMULATED_WRONG_STORY_FACT = [
    'hallo',
    'Hallo! Ich bin Thilio. Wir haben die Geschichte von Pia geh\u00f6rt. '
    'Pia macht morgens ganz viel. Was hat Pia ihrem Hamster Hubert gegeben?',
    'Marmelade',
]


# ---------------------------------------------------------------------------
# Strategy A — fixture-based tests
# ---------------------------------------------------------------------------


@pytest.mark.llm_feature
@pytest.mark.llm_judge
class TestIncorrectStoryFactsFixtureBased:
    """Strategy A: Verify gentle correction of wrong story facts."""

    def test_gentle_correction_with_confirmation(
        self, system_llm, judge_llm, n_runs, pass_threshold, run_details_recorder
    ):
        """
        Example 1 (PIA): Child says 'Lisa und sarah' for friends' names.
        System should correct ('Millie und Sarah') AND check if child
        now remembers (small confirmation). Should NOT just move on.
        """
        state = build_state(
            child_name="Emma",
            child_age=6,
            child_gender="weiblich",
            messages=_script_to_messages(SCRIPT_WRONG_FRIEND_NAMES),
            audio_book=FIXTURE_PIA_AUDIO_BOOK,
            story_id=FIXTURE_PIA_STORY_ID,
            chapter_id=FIXTURE_PIA_CHAPTER_ID,
        )

        def _run() -> tuple[bool, str, str]:
            from nodes import masterChatbot
            result = masterChatbot(state, system_llm)
            spoken_text = result["messages"][-1].content
            return llm_judge(judge_llm, spoken_text, CRITERION_GENTLE_CORRECTION_WITH_CONFIRMATION)

        run_details_recorder(
            _run, n_runs, pass_threshold,
            setting=state_to_setting(state, CRITERION_GENTLE_CORRECTION_WITH_CONFIRMATION),
        )

    def test_short_direct_correction(
        self, system_llm, judge_llm, n_runs, pass_threshold, run_details_recorder
    ):
        """
        Example 2 (BOBO): Child says 'er sagt ja' about what Bobo does
        when Mama asks. System should give correct answer directly
        ('Bobo sagt nichts, er ist eingeschlafen') without lengthy
        commentary. Must not sound critical.
        """
        state = build_state(
            child_name="Emma",
            child_age=5,
            child_gender="weiblich",
            messages=_script_to_messages(SCRIPT_BOBO_WRONG_ANSWER),
            audio_book=FIXTURE_BOBO_AUDIO_BOOK,
            story_id=FIXTURE_BOBO_STORY_ID,
            chapter_id=FIXTURE_BOBO_CHAPTER_ID,
        )

        def _run() -> tuple[bool, str, str]:
            from nodes import masterChatbot
            result = masterChatbot(state, system_llm)
            spoken_text = result["messages"][-1].content
            return llm_judge(judge_llm, spoken_text, CRITERION_SHORT_DIRECT_CORRECTION)

        run_details_recorder(
            _run, n_runs, pass_threshold,
            setting=state_to_setting(state, CRITERION_SHORT_DIRECT_CORRECTION),
        )

    def test_neutral_fact_correction(
        self, system_llm, judge_llm, n_runs, pass_threshold, run_details_recorder
    ):
        """
        Example 3 (PIA): Child says wrong food for Hubert.
        System should incorporate correct information neutrally,
        not react correctively or judgmentally.
        """
        state = build_state(
            child_name="Emma",
            child_age=6,
            child_gender="weiblich",
            messages=_script_to_messages(SCRIPT_WRONG_HUBERT_FOOD),
            audio_book=FIXTURE_PIA_AUDIO_BOOK,
            story_id=FIXTURE_PIA_STORY_ID,
            chapter_id=FIXTURE_PIA_CHAPTER_ID,
        )

        def _run() -> tuple[bool, str, str]:
            from nodes import masterChatbot
            result = masterChatbot(state, system_llm)
            spoken_text = result["messages"][-1].content
            return llm_judge(judge_llm, spoken_text, CRITERION_NEUTRAL_FACT_CORRECTION)

        run_details_recorder(
            _run, n_runs, pass_threshold,
            setting=state_to_setting(state, CRITERION_NEUTRAL_FACT_CORRECTION),
        )


# ---------------------------------------------------------------------------
# Strategy B — fully-simulated tests
# ---------------------------------------------------------------------------


@pytest.mark.llm_feature
@pytest.mark.llm_judge
@pytest.mark.simulated
class TestIncorrectStoryFactsSimulated:
    """
    Strategy B: Run the full conversation from scratch using real LLMs.

    Uses SIMULATED_N_RUNS (default: 3) because each run involves multiple
    real LLM calls.
    """

    def test_neutral_fact_correction_simulated(
        self, system_llm, judge_llm, pass_threshold, run_details_recorder
    ):
        """
        Example 3 (PIA): Full simulation where the child gives a wrong
        answer about Hubert's food. The final system response should
        correct neutrally without judgment.
        """
        n = _cfg.SIMULATED_N_RUNS

        def _run() -> tuple:
            final_state, spoken_text = simulate_conversation(
                system_llm_instance=system_llm,
                child_name="Emma",
                child_age=6,
                child_gender="weiblich",
                child_inputs=SIMULATED_WRONG_STORY_FACT,
                audio_book=FIXTURE_PIA_AUDIO_BOOK,
                story_id=FIXTURE_PIA_STORY_ID,
                chapter_id=FIXTURE_PIA_CHAPTER_ID,
            )
            passed, resp, reason = llm_judge(
                judge_llm, spoken_text, CRITERION_NEUTRAL_FACT_CORRECTION,
            )
            from langchain_core.messages import HumanMessage as _HM
            conversation = [
                {"role": "Child" if isinstance(m, _HM) else "System", "content": m.content}
                for m in final_state.get("messages", [])
            ]
            return passed, resp, reason, conversation

        run_details_recorder(
            _run, n, pass_threshold,
            setting=simulation_to_setting(
                "Emma", 6, "weiblich",
                SIMULATED_WRONG_STORY_FACT,
                CRITERION_NEUTRAL_FACT_CORRECTION,
            ),
        )
