from myutils import line
from langchain_community.document_loaders import TextLoader
from langchain_text_splitters import CharacterTextSplitter, RecursiveCharacterTextSplitter


def main():
    pto_path = "data/pto_and_parental_leave_policy.txt"
    handbook_path = "data/global_employee_handbook.txt"

    pto_docs = TextLoader(pto_path, encoding="utf-8").load()
    handbook_docs = TextLoader(handbook_path, encoding="utf-8").load()

    print(f"Loaded PTO: {len(pto_docs[0].page_content)} characters")
    print(f"Loaded Handbook: {len(handbook_docs[0].page_content)} characters")

    splitter = CharacterTextSplitter(chunk_size=400, chunk_overlap=0)
    chunks = splitter.split_documents(pto_docs)
    print(f"The splitter created {len(chunks)} chunks")     # print the number of chunks
    print([len(c.page_content) for c in chunks])            # print the chunk sizes

    line()

    splitter = RecursiveCharacterTextSplitter(
        separators=["\n", "\n\n", "", " "],
        chunk_overlap=50,
        chunk_size=500,
        add_start_index=True
    )
    chunks = splitter.split_documents(handbook_docs)
    for idx, chunk in enumerate(chunks):
        print(f"Chunk {idx}: {len(chunk.page_content)} characters. Source: {chunk.metadata.get("source")}")


if __name__ == '__main__':
    line()
    main()
    line()
