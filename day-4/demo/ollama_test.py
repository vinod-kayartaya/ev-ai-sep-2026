from langchain_ollama import ChatOllama

llm = ChatOllama(
    model="qwen3:8b",
    base_url="http://127.0.0.1:11434",
)

for chunk in llm.stream("Tell me a joke"):
    print(chunk.content, end="", flush=True)
