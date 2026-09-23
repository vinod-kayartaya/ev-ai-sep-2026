from langchain import LangChain

# Initialize LangChain with some sample configuration
lc = LangChain(mode='chat', temperature=0.5)

# Add a conversation history
lc.add_to_history('user', 'What is LangChain?')

# Generate a response
response = lc.generate_response()

# Print the output
print('LangChain response:', response)