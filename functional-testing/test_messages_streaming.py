#!/usr/bin/env python3
"""Test if the streaming deduplication fixes garbled output"""
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

config = {'configurable': {'thread_id': 'test_dedup'}}
set_config(config)

print('Testing streaming with deduplication...\n')
msg = HumanMessage(content="Tell me about dinosaurs")

print('🤖 Lino: ', end='', flush=True)

seen_message_ids = set()
seen_content = ""

for event in im_graph.stream({'messages': [msg]}, config, stream_mode='messages'):
    if isinstance(event, tuple):
        message, metadata = event
        node = metadata.get('langgraph_node', '')

        if node == 'format_response':
            msg_id = getattr(message, 'id', None)
            if msg_id and msg_id in seen_message_ids:
                continue

            if hasattr(message, 'content') and message.content:
                if len(message.content) > len(seen_content):
                    new_content = message.content[len(seen_content):]
                    print(new_content, end='', flush=True)
                    seen_content = message.content

                if msg_id:
                    seen_message_ids.add(msg_id)

print(f'\n\n✅ Complete output length: {len(seen_content)} characters')
print(f'✅ Total unique messages: {len(seen_message_ids)}')
print('\nIf the text above looks clean and coherent, the fix worked!')
