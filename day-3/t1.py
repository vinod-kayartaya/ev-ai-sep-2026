from typing import TypedDict
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv
from langgraph.graph import StateGraph, START, END


load_dotenv()
llm = ChatOpenAI(model="gpt-4o-mini")

class State(TypedDict):
    question: str
    answer: str


def find_answer(state: State) -> State:
    resp = llm.invoke(state["question"])
    return {
        "answer": resp.content
    }


def main():
    graph_builder = StateGraph(State)
    graph_builder.add_node("find_answer", find_answer)
    graph_builder.add_edge(START, "find_answer")
    graph_builder.add_edge("find_answer", END)

    graph = graph_builder.compile()

    initial_state = {
        "question": input("Enter your prompt: ")
    }

    result = graph.invoke(initial_state)
    print(result["answer"])

if __name__ == "__main__":
    main()
