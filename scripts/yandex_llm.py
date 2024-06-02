import os
from tqdm import tqdm
from dotenv import load_dotenv
from yandex_chain import YandexLLM, YandexEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_community.document_loaders import TextLoader
from langchain_community.document_loaders.pdf import PDFMinerLoader
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

    for path in tqdm(os.listdir('../files/pdfs/all_docs')):
        pdf_path = '../files/pdfs/all_docs/'+path
        loader = PDFMinerLoader(pdf_path)
        document = loader.load()
        doc = text_splitter.split_documents(document)
        db = FAISS.from_documents(doc, embedding=embeddings)  # .from_documents(doc, embeddings)
    
    db.save_local(folder_path, index_name)

    return db


def load_embeddings(folder_path: str, index_name: str) -> FAISS:
    embeddings = YandexEmbeddings(folder_id=os.getenv('FOLDER_ID'), api_key=os.getenv('YANDEX_API_KEY'))
    db = FAISS.load_local(folder_path=folder_path, embeddings=embeddings, index_name=index_name, allow_dangerous_deserialization=True)
    return db


def rag_system(query: str, db_folder_path: str, db_index_name: str):
    # print(" + Индексируем документы")
    # db = create_embeddings_with_text('../files/dbs/db1_text', index_name='finance_docs') Создаем базу данных, если ее нет
    # db = create_embeddings_with_pdf('../files/dbs/db1_pdf', index_name='finance_docs') Второй варинант создания без custom pdf_parser
    db =  load_embeddings(folder_path=db_folder_path, index_name=db_index_name)
    retriever = db.as_retriever()

    # print(f"+ Запрос: {query}")
    # print(" + Получение релевантных документов")
    retriever = db.as_retriever()
    # docs = retriever.invoke(query) На будущее
    # print(docs[0].page_content) по этому print можно будет определить в каком месте плохо сформирован текст pdf парсером

    template = """Ответь на вопрос, основываясь только на текст ниже. Плюс сначала пиши название текста и через 2 строчки ответ.
    Еще учитывай, что ты отлично разбираешься в финансовых отчетах и бухгалтерском учете в целом.
    Также помни ты получаешь данные из нескольких документов в общей базе данных:
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

    # print(" + Запуск LLM Chain")
    res = chain.invoke(query)
    print(f" + Ответ: {res}")




def main():
    while True:
        query = input('Введите ваш запрос (или q для выхода): ')
        if query == 'q': break
        rag_system(query=query, db_folder_path='../files/dbs/db1_text', db_index_name='finance_docs')
        print('\n\n' + 100*'=' + '\n\n')


if __name__ == "__main__":
    main()