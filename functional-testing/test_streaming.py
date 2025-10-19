#!/usr/bin/env python3
"""Quick test to verify streaming works with custom mode"""
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

print('Testing custom streaming mode...')
msg = HumanMessage(content='Say hello in 3 words')

print('\n🤖 Response: ', end='', flush=True)
chunk_count = 0
for event in im_graph.stream({'messages': [msg]}, config, stream_mode='custom'):
    if isinstance(event, tuple) and len(event) == 2:
        node_name, data = event
        if node_name == 'format_response' and isinstance(data, dict):
            if data.get('type') == 'chunk' and 'content' in data:
                chunk_count += 1
                print(data['content'], end='', flush=True)

print(f'\n\n✅ Received {chunk_count} streaming chunks from format_response node')
print('✅ If chunks > 0, streaming is working!')
