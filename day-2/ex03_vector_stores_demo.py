import os
import sys

from myutils import line
from dotenv import load_dotenv
from langchain_openai import OpenAIEmbeddings
from langchain_community.document_loaders import TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_community.callbacks import get_openai_callback


def init():
    global model_name
    load_dotenv()   # loads environment variables from .env file
    model_name = os.environ.get("OPENAI_MODEL_NAME")
    if not os.environ.get("OPENAI_API_KEY"):
        print("OPENAI_API_KEY is required, but missing!")
        sys.exit(1)


def main():
    init()
    files = [
        "data/global_employee_handbook.txt",
        "data/health_benefits_and_insurance_guide.txt",
        "data/pto_and_parental_leave_policy.txt"
    ]

    docs = []
    for file in files:
        docs += TextLoader(file, encoding="utf-8").load()

    print(f"Got {len(docs)} documents")
    splitter = RecursiveCharacterTextSplitter(
        separators=["\n\n", "\n", "", " "],
        chunk_size=500,
        chunk_overlap=50
    )
    chunks = splitter.split_documents(docs)
    print(f"Got {len(chunks)} chunks")

    user_input = input("Enter your query: ")

    with get_openai_callback() as cb:
        embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
        vector_store = FAISS.from_documents(chunks, embeddings)
        result = vector_store.similarity_search_with_score(query=user_input, k=3)

        print(f"Prompt (input) tokens: {cb.prompt_tokens}")
        print(f"Completion (output) tokens: {cb.completion_tokens}")
        print(f"Total tokens: {cb.total_tokens}")
        print(f"Estimated total cost (USD): {cb.total_cost:.8f}")


    for chunk, score in result:
        print(f"Source={chunk.metadata.get("source")}, Score={score}")
        print(chunk.page_content)
        print()

    line()

    result = vector_store.as_retriever(search_kwargs={"k":3}).invoke(user_input)
    for chunk in result:
        print(chunk.page_content)
        line(char=".")


if __name__ == '__main__':
    line()
    main()
    line()
