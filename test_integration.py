#!/usr/bin/env python
# Test script to verify Flask app and Core_Brain integration
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import the integration layer and other components
from zen_flask.ai_integration.integration import get_integration, get_response, analyze_text, speech_to_text, text_to_speech
from Core_Brain import memory, get_core_status, is_core_ready

print("===== EchoV1 Integration Test =====")

# Check core components status
print("\n1. Checking Core Brain status...")
status = get_core_status()
print(f"Core ready: {is_core_ready()}")
for component, ready in status.items():
    print(f"  {component}: {'✓ Ready' if ready else '✗ Not ready'}")

# Test integration layer
print("\n2. Testing integration layer...")
integration = get_integration()
print(f"Integration initialized: {integration.core_initialized}")

# Test basic text response
test_message = "Hello, how are you today?"
print(f"\n3. Testing text response with message: '{test_message}'")
response = get_response(test_message, memory_manager=memory, personality_name="echo")
print(f"Response success: {response.get('success')}")
print(f"Response text: {response.get('response')}")

# Test message analysis
print(f"\n4. Testing message analysis for: '{test_message}'")
analysis = analyze_text(test_message, memory_manager=memory)
print(f"Analysis success: {analysis.get('success')}")
print(f"Intent: {analysis.get('analysis', {}).get('intent')}")
print(f"Emotion: {analysis.get('analysis', {}).get('emotion')}")
print(f"Sentiment: {analysis.get('analysis', {}).get('sentiment')}")

# Test personality switching
print("\n5. Testing personality switching...")
suzi_response = get_response("Tell me a joke", memory_manager=memory, personality_name="Suzi")
print(f"Suzi response: {suzi_response.get('response')}")

# Test memory integration
print("\n6. Testing memory integration...")
if memory:
    # Add a memory
    memory.add_memory(test_message, response.get('response'))
    # Get recent memories
    recent_memories = memory.get_recent_memories(2)
    print(f"Recent memories count: {len(recent_memories) if recent_memories else 0}")
    if recent_memories:
        print("Most recent memory:")
        print(f"  User: {recent_memories[0].get('user_input')}")
        print(f"  AI: {recent_memories[0].get('ai_response')}")
else:
    print("Memory manager not available")

# Note about speech tests
print("\nNote: Speech-to-text and text-to-speech tests require audio input/output and are not automatically performed in this script.")
print("\n===== Integration Test Complete =====")