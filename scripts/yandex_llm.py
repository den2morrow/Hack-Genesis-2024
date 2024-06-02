import os
from tqdm import tqdm
from dotenv import load_dotenv
from yandex_chain import YandexLLM, YandexEmbeddings
from langchain.vectorstores import FAISS
from langchain_community.document_loaders import TextLoader
from langchain_community.document_loaders.pdf import UnstructuredPDFLoader
from langchain_text_splitters import CharacterTextSplitter, RecursiveCharacterTextSplitter
from langchain.prompts import ChatPromptTemplate
from langchain.schema.output_parser import StrOutputParser
from langchain.schema.runnable import RunnablePassthrough

load_dotenv()


def create_embeddings_with_text(folder_path: str, index_name: str) -> FAISS:
    embeddings = YandexEmbeddings(folder_id=os.getenv('FOLDER_ID'), api_key=os.getenv('YANDEX_API_KEY'))
    # text_splitter = CharacterTextSplitter(chunk_size=2000, chunk_overlap=0)
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=0)

    for path in tqdm(os.listdir('../files/txts')):
        txt_path = '../files/txts/'+path
        loader = TextLoader(txt_path)
        document = loader.load()
        doc = text_splitter.split_documents(document)
        db = FAISS.from_documents(doc, embeddings)
    
    db.save_local(folder_path, index_name)

    return db


def create_embeddings_with_pdf(folder_path: str, index_name: str) -> FAISS:
    embeddings = YandexEmbeddings(folder_id=os.getenv('FOLDER_ID'), api_key=os.getenv('YANDEX_API_KEY'))
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=0)

    for path in tqdm(os.listdir('../files/all_docs')):
        pdf_path = '../files/all_docs/'+path
        loader = UnstructuredPDFLoader(pdf_path)
        document = loader.load()
        doc = text_splitter.split_documents(document)
        db = FAISS.from_documents(doc, embedding=embeddings)  # .from_documents(doc, embeddings)
    
    db.save_local(folder_path, index_name)

    return db


def load_embeddings(folder_path: str, index_name: str) -> FAISS:
    embeddings = YandexEmbeddings(folder_id=os.getenv('FOLDER_ID'), api_key=os.getenv('YANDEX_API_KEY'))
    db = FAISS.load_local(folder_path=folder_path, embeddings=embeddings, index_name=index_name, allow_dangerous_deserialization=True)
    return db


def main():
    print(" + Индексируем документы")
    # db = create_embeddings_with_text('../files/db1_text/', index_name='finance_docs')
    # db = create_embeddings_with_pdf('../files/db1_pdf/', index_name='finance_docs')
    db =  load_embeddings('../files/db/', index_name='finance_docs')
    retriever = db.as_retriever()

    query = "На сколько снизится экономика в 2023 году?"
    print(f"+ Запрос: {query}")

    print(" + Получение релевантных документов")
    retriever = db.as_retriever()

    template = """Ответь на вопрос, основываясь только на текст ниже:
    {context}

    Вопрос: {question}
    """

    prompt = ChatPromptTemplate.from_template(template)
    model = YandexLLM(folder_id=os.getenv('FOLDER_ID'), api_key=os.getenv('YANDEX_API_KEY'))

    chain = (
        {"context": retriever, "question": RunnablePassthrough()} 
        | prompt 
        | model 
        | StrOutputParser()
    )

    print(" + Запуск LLM Chain")
    res = chain.invoke(query)
    print(f" + Ответ: {res}")


if __name__ == "__main__":
    main()