"""
Background analysis graph for analyzing conversations asynchronously.
"""
from langgraph.graph import StateGraph, START, END
from states import BackgroundState
from nodes import (
    initialStateLoader,
    speechGrammarWorker,
    speechComprehensionWorker,
    sprachhandlungsAnalyseWorker,
    speechVocabularyWorker,
    boredomWorker,
    foerderfokusWorker,
    aufgabenWorker,
    satzbauAnalyseWorker,
    satzbauBegrenzungsWorker,
    background_graph_needs_initial_state
)


def create_background_analysis_graph(llm, memory):
    """
    Create and compile the background analysis graph.

    :param llm: Language model instance
    :param memory: Memory checkpointer
    :return: Compiled graph
    """
    builder = StateGraph(BackgroundState)

    # Add nodes with LLM binding
    builder.add_node("initialStateLoader", initialStateLoader)

    builder.add_node("satzbauAnalyseWorker", lambda state, config: satzbauAnalyseWorker(state, config, llm))
    builder.add_node("satzbauBegrenzungsWorker", lambda state, config: satzbauBegrenzungsWorker(state, config, llm))

    # Add edges
    builder.add_conditional_edges(START, background_graph_needs_initial_state)
    builder.add_edge("initialStateLoader", "satzbauAnalyseWorker")

    builder.add_edge("satzbauAnalyseWorker", "satzbauBegrenzungsWorker")

    builder.add_edge("satzbauBegrenzungsWorker", END)

    return builder.compile(checkpointer=memory)
