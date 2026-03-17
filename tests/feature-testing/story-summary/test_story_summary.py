"""
Feature: Story Summary (Kurzfassung des Textes wiedergeben)
Test file: When the child asks for a story retelling, the system should
provide a shortened version covering the most important plot points.

Three sub-behaviours are tested:
  1. Short retelling on request: child explicitly asks for a retelling,
     system gives a shortened version and then asks how the child found
     the story or an open question (not detail questions).
  2. Proactive retelling offer: after multiple content errors, system may
     proactively offer to retell. After retelling, ask about the main idea
     and build a short conversation.
  3. Summary only key points: when retelling, only the most important plot
     points are summarized. After summary, ask an open question about the
     story or child's opinion, not detail questions.

Story used: "Pia muss nicht perfekt sein"

Two strategies are tested:
  Strategy A -- fixture-based (fast, reproducible)
  Strategy B -- fully simulated (realistic, end-to-end)

Markers:
  llm_feature   -- all tests here (real LLM involved)
  llm_judge     -- LLM judge is called
  simulated     -- Strategy B tests only
"""

import pytest
from langchain_core.messages import HumanMessage, AIMessage

from feature_testing_utils import (
    build_state,
    llm_judge,
    simulate_conversation,
    state_to_setting,
    simulation_to_setting,
    FIXTURE_PIA_AUDIO_BOOK,
    FIXTURE_PIA_STORY_ID,
    FIXTURE_PIA_CHAPTER_ID,
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
# Conversation scripts
# ---------------------------------------------------------------------------

# Example 1: Child explicitly asks for a story retelling
SCRIPT_SHORT_RETELLING_ON_REQUEST = [
    # child
    'hallo',
    # system
    'Hallo! Ich bin Thilio, dein Sprachbegleiter.'
    ' Wir haben gerade die Geschichte von Pia geh\u00f6rt,'
    ' die immer alles richtig macht.'
    ' Wei\u00dft du noch, was Pia als Erstes am Freitag gemacht hat?',
    # child
    'socken',
    # system
    'Ja, Pia hat Socken angezogen, die zusammenpassen.'
    ' Pia hat auch Hubert gef\u00fcttert.'
    ' Was hat Hubert zu essen bekommen?',
    # child
    'brokkoli',
    # system
    'Genau, Hubert hat Brokkoli bekommen.'
    ' Sp\u00e4ter war Pia beim Talentwettbewerb.'
    ' Was ist dort passiert?',
    # child
    'wei\u00df nicht mehr so genau',
    # system
    'Kein Problem! Pia hat beim Talentwettbewerb jongliert.'
    ' Aber dann ist etwas schiefgegangen.'
    ' Der Ballon ist geplatzt und alles ist auf Pia gefallen.',
    # child — TESTED: child asks for retelling
    'Kannst du die Geschichte nochmal erz\u00e4hlen?',
]

# Example 2: After multiple content errors, system may proactively offer retelling
SCRIPT_PROACTIVE_RETELLING_OFFER = [
    # child
    'hallo',
    # system
    'Hallo! Ich bin Thilio.'
    ' Wir haben die Geschichte von Pia geh\u00f6rt.'
    ' Wei\u00dft du, was Pia am Morgen gemacht hat?',
    # child
    'sie hat ferngesehen',
    # system
    'Das stimmt nicht ganz. Pia hat Socken angezogen.'
    ' Was hat Pia ihrem Hamster Hubert gegeben?',
    # child
    'schokolade',
    # system
    'Nicht ganz. Hubert hat Brokkoli bekommen.'
    ' Was haben die Leute Pia gefragt?',
    # child
    'ob sie einen hund hat',
    # system
    'Das war es nicht. Die Leute haben gefragt, ob Pia ihr Bett gemacht hat.'
    ' Pia macht immer alles richtig.'
    ' Was ist beim Talentwettbewerb passiert?',
    # child — TESTED: another wrong answer after multiple errors
    'sie hat gesungen',
]

# Example 3: Child asks for retelling — system should summarize only key points
SCRIPT_SUMMARY_ONLY_KEY_POINTS = [
    # child
    'hallo',
    # system
    'Hallo! Ich bin Thilio.'
    ' Wir haben gerade die Geschichte von Pia geh\u00f6rt.'
    ' Pia macht immer alles richtig.'
    ' Wei\u00dft du, was sie am Morgen gemacht hat?',
    # child
    'socken angezogen',
    # system
    'Genau! Pia hat Socken angezogen, die zusammenpassen.'
    ' Sp\u00e4ter gab es einen Talentwettbewerb.'
    ' Was ist da passiert?',
    # child
    'der ballon ist geplatzt',
    # system
    'Ja! Der Ballon ist geplatzt und Hubert wurde nass.'
    ' Was hat Pia dann gemacht?',
    # child
    'sie hat gelacht',
    # system
    'Genau, Pia hat gelacht!'
    ' Das war eine tolle Geschichte, oder?',
    # child — TESTED: child asks for retelling
    'Kannst du mir die Geschichte nochmal erz\u00e4hlen?',
]


# ---------------------------------------------------------------------------
# Judge criteria (English)
# ---------------------------------------------------------------------------

CRITERION_SHORT_RETELLING_ON_REQUEST = (
    "The child explicitly asked: 'Kannst du die Geschichte nochmal "
    "erz\u00e4hlen?' (Can you retell the story?). Does the system response "
    "provide a SHORTENED retelling of the Pia story (covering the main plot "
    "points without going through every single detail)? After the retelling, "
    "does the system ask an open question such as how the child found the "
    "story, whether they liked it, or what they thought about it — rather "
    "than asking specific detail/comprehension questions? "
    "Return PASS if the system gives a shortened retelling AND follows up "
    "with an open question or asks how the child liked the story, "
    "FAIL if the system refuses to retell, gives an excessively detailed "
    "retelling, or follows up with specific detail questions."
)

CRITERION_PROACTIVE_RETELLING_OFFER = (
    "The child has made multiple content errors throughout the conversation "
    "(gave wrong answers about the story several times). Does the system "
    "response either: (a) proactively offer to retell the story to help the "
    "child, OR (b) correct the child and provide a supportive bridge such as "
    "a short summary of what actually happened? After any retelling or "
    "summary, does it ask about the main idea or build a short conversation "
    "rather than continuing with more detail questions? "
    "Return PASS if the system offers to retell or provides a helpful summary "
    "after the child's repeated errors, and moves toward discussing the main "
    "idea or the child's opinion, "
    "FAIL if the system simply corrects and asks another detail question "
    "without acknowledging the pattern of errors or offering help."
)

CRITERION_SUMMARY_ONLY_KEY_POINTS = (
    "The child asked for a story retelling. Does the system response "
    "summarize ONLY the most important plot points of the Pia story "
    "(e.g. Pia always does everything right, she has a talent show, "
    "something goes wrong, she laughs about it) without going into "
    "excessive detail about every scene? After the summary, does the "
    "system ask an OPEN question about the story or the child's opinion "
    "(e.g. 'Wie fandest du die Geschichte?', 'Was denkst du dar\u00fcber?') "
    "rather than a specific detail question? "
    "Return PASS if the retelling is concise (covers key points only) AND "
    "is followed by an open question about the story or the child's opinion, "
    "FAIL if the retelling is excessively detailed or if the follow-up "
    "question is a specific detail/comprehension question."
)


# ---------------------------------------------------------------------------
# Simulated child inputs for Strategy B (ODD length — ends with child utterance)
# ---------------------------------------------------------------------------

SIMULATED_CHILD_RETELLING_REQUEST = [
    'hallo',
    'Hallo! Ich bin Thilio. Wir haben die Geschichte von Pia geh\u00f6rt. '
    'Wei\u00dft du noch, was Pia am Freitag gemacht hat?',
    'socken angezogen',
    'Ja, Pia hat Socken angezogen. Und was ist beim Talentwettbewerb passiert?',
    'der ballon ist geplatzt',
    'Genau! Der Ballon ist geplatzt. Was hat Pia dann gemacht?',
    'gelacht',
    'Ja, Pia hat gelacht! Das war lustig, oder?',
    'Kannst du die Geschichte nochmal erz\u00e4hlen?',
]


# ---------------------------------------------------------------------------
# Strategy A — fixture-based tests
# ---------------------------------------------------------------------------

@pytest.mark.llm_feature
@pytest.mark.llm_judge
class TestStorySummaryFixtureBased:
    """Strategy A: Verify the system provides a shortened retelling when asked."""

    def test_short_retelling_on_request(
        self, system_llm, judge_llm, n_runs, pass_threshold, run_details_recorder
    ):
        """
        Example 1: Child explicitly asks 'Kannst du die Geschichte nochmal
        erz\u00e4hlen?' System should give a shortened retelling and then ask
        an open question (how did you find the story, did you like it).
        """
        state = build_state(
            child_name="Emma",
            child_age=5,
            child_gender="weiblich",
            messages=_script_to_messages(SCRIPT_SHORT_RETELLING_ON_REQUEST),
            audio_book=FIXTURE_PIA_AUDIO_BOOK,
            story_id=FIXTURE_PIA_STORY_ID,
            chapter_id=FIXTURE_PIA_CHAPTER_ID,
        )

        def _run() -> tuple[bool, str, str]:
            from nodes import masterChatbot
            result = masterChatbot(state, system_llm)
            spoken_text = result["messages"][-1].content
            return llm_judge(judge_llm, spoken_text, CRITERION_SHORT_RETELLING_ON_REQUEST)

        run_details_recorder(
            _run, n_runs, pass_threshold,
            setting=state_to_setting(state, CRITERION_SHORT_RETELLING_ON_REQUEST),
        )

    def test_proactive_retelling_offer(
        self, system_llm, judge_llm, n_runs, pass_threshold, run_details_recorder
    ):
        """
        Example 2: After multiple content errors by the child, the system
        should proactively offer to retell or provide a helpful summary.
        After retelling, ask about the main idea.
        """
        state = build_state(
            child_name="Emma",
            child_age=5,
            child_gender="weiblich",
            messages=_script_to_messages(SCRIPT_PROACTIVE_RETELLING_OFFER),
            audio_book=FIXTURE_PIA_AUDIO_BOOK,
            story_id=FIXTURE_PIA_STORY_ID,
            chapter_id=FIXTURE_PIA_CHAPTER_ID,
        )

        def _run() -> tuple[bool, str, str]:
            from nodes import masterChatbot
            result = masterChatbot(state, system_llm)
            spoken_text = result["messages"][-1].content
            return llm_judge(judge_llm, spoken_text, CRITERION_PROACTIVE_RETELLING_OFFER)

        run_details_recorder(
            _run, n_runs, pass_threshold,
            setting=state_to_setting(state, CRITERION_PROACTIVE_RETELLING_OFFER),
        )

    def test_summary_only_key_points(
        self, system_llm, judge_llm, n_runs, pass_threshold, run_details_recorder
    ):
        """
        Example 3: Child asks for retelling. System should summarize only the
        most important plot points and follow up with an open question about
        the story or child's opinion.
        """
        state = build_state(
            child_name="Emma",
            child_age=5,
            child_gender="weiblich",
            messages=_script_to_messages(SCRIPT_SUMMARY_ONLY_KEY_POINTS),
            audio_book=FIXTURE_PIA_AUDIO_BOOK,
            story_id=FIXTURE_PIA_STORY_ID,
            chapter_id=FIXTURE_PIA_CHAPTER_ID,
        )

        def _run() -> tuple[bool, str, str]:
            from nodes import masterChatbot
            result = masterChatbot(state, system_llm)
            spoken_text = result["messages"][-1].content
            return llm_judge(judge_llm, spoken_text, CRITERION_SUMMARY_ONLY_KEY_POINTS)

        run_details_recorder(
            _run, n_runs, pass_threshold,
            setting=state_to_setting(state, CRITERION_SUMMARY_ONLY_KEY_POINTS),
        )


# ---------------------------------------------------------------------------
# Strategy B — fully-simulated tests
# ---------------------------------------------------------------------------

@pytest.mark.llm_feature
@pytest.mark.llm_judge
@pytest.mark.simulated
class TestStorySummarySimulated:
    """Strategy B: Full simulation where child asks for a story retelling."""

    def test_retelling_request_simulated(
        self, system_llm, judge_llm, pass_threshold, run_details_recorder
    ):
        """
        Full simulation: child discusses the Pia story and then asks for a
        retelling. The final system response should be a shortened retelling
        followed by an open question.
        """
        n = _cfg.SIMULATED_N_RUNS

        def _run() -> tuple:
            final_state, spoken_text = simulate_conversation(
                system_llm_instance=system_llm,
                child_name="Emma",
                child_age=5,
                child_gender="weiblich",
                child_inputs=SIMULATED_CHILD_RETELLING_REQUEST,
                audio_book=FIXTURE_PIA_AUDIO_BOOK,
                story_id=FIXTURE_PIA_STORY_ID,
                chapter_id=FIXTURE_PIA_CHAPTER_ID,
            )
            passed, resp, reason = llm_judge(
                judge_llm, spoken_text, CRITERION_SHORT_RETELLING_ON_REQUEST
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
                "Emma", 5, "weiblich",
                SIMULATED_CHILD_RETELLING_REQUEST,
                CRITERION_SHORT_RETELLING_ON_REQUEST,
            ),
        )
