#!/usr/bin/env python3
"""Quick test to verify streaming works with custom mode"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'agentic-system'))

from immediate_graph import create_immediate_response_graph
from background_graph import create_background_analysis_graph
from nodes import set_background_graph
from immediate_graph import set_config
from langchain.chat_models import init_chat_model
from langchain_core.messages import HumanMessage
from langgraph.checkpoint.memory import MemorySaver
from dotenv import load_dotenv

load_dotenv()
llm = init_chat_model('google_genai:gemini-2.0-flash')
memory = MemorySaver()
bg_graph = create_background_analysis_graph(llm, memory)
set_background_graph(bg_graph)
im_graph = create_immediate_response_graph(llm, memory, bg_graph)

config = {'configurable': {'thread_id': 'test123'}}
set_config(config)

print('Testing messages streaming mode...')
msg = HumanMessage(content='Say hello in 3 words')

print('\n🤖 Response: ', end='', flush=True)
chunk_count = 0
# stream_mode='messages' emits (message_chunk, metadata) tuples for every LLM token
for msg_chunk, metadata in im_graph.stream({'messages': [msg]}, config, stream_mode='messages'):
    if hasattr(msg_chunk, 'content') and msg_chunk.content:
        chunk_count += 1
        print(msg_chunk.content, end='', flush=True)

print(f'\n\n✅ Received {chunk_count} streaming chunks')
print('✅ If chunks > 0, streaming is working!')
print()
print('NOTE: The graph has no "format_response" node and no custom StreamWriter calls.')
print('      stream_mode="custom" only emits events when nodes explicitly call StreamWriter.')
print('      Use stream_mode="messages" to stream LLM tokens automatically.')
