import os
import sys

from myutils import line
from dotenv import load_dotenv
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser
from langchain_community.document_loaders import TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS


def init():
    global model_name
    load_dotenv()   # loads environment variables from .env file
    model_name = os.environ.get("OPENAI_MODEL_NAME")
    if not os.environ.get("OPENAI_API_KEY"):
        print("OPENAI_API_KEY is required, but missing!")
        sys.exit(1)


def get_formatted_content(docs) -> str:
    """
    Returns a single str object containg all chunks in the docs (input parameter)
    """
    output = ""
    for doc in docs:
        source = doc.metadata.get("source")
        output += f"Content={doc.page_content} [Source={source}]"
    return output


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


    embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
    vector_store = FAISS.from_documents(chunks, embeddings)
    retriever = vector_store.as_retriever(kwargs={"k":4})

    llm = ChatOpenAI(model=os.environ.get("OPENAI_MODEL_NAME"), temperature=0.0)

    prompt = ChatPromptTemplate.from_messages([
        ("system", "You are human resource and employee relationship policy assistant. "
            "Answer the user query purely based on the context given. "
            "At the end, include the source of the finding from the context."
            "If you do not find the answer, respond with 'I do not have information for your query'."
            "Do not speculate or give random answer.\n"
            "Context: {context}"),
        ("human", "{query}")
    ])

    user_input = input("Enter your query: ")
    retriever.invoke(user_input)

    # RAG LECL chain
    rag_chain = (
        {       
            "context": retriever | get_formatted_content,
            "query": RunnablePassthrough()
        } 
        | 
        prompt 
        | llm 
        | StrOutputParser()
    )
    
    resp = rag_chain.invoke(user_input)
    print(resp)


if __name__ == '__main__':
    line()
    main()
    line()
