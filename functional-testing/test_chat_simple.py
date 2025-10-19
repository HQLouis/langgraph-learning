#!/usr/bin/env python3
"""Simple test to verify chat works end-to-end"""
import sys
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

config = {'configurable': {'thread_id': 'test_final'}}
set_config(config)

print('🧪 Testing chat functionality...\n')
msg = HumanMessage(content='Say hi in 5 words')

print('👤 User: Say hi in 5 words')
print('🤖 Lino: ', end='', flush=True)

response_found = False
for event in im_graph.stream({'messages': [msg]}, config, stream_mode='updates'):
    for node_name, node_output in event.items():
        if node_name == 'format_response' and 'messages' in node_output:
            for m in node_output['messages']:
                if hasattr(m, 'content') and m.content and hasattr(m, 'type') and m.type == 'ai':
                    print(m.content, flush=True)
                    response_found = True

if response_found:
    print('\n✅ SUCCESS! Chat is working correctly.')
    sys.exit(0)
else:
    print('\n❌ FAILED! No response found.')
    sys.exit(1)

