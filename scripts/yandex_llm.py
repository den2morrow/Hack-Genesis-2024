import os
from dotenv import load_dotenv
from yandex_chain import YandexLLM, YandexEmbeddings
from langchain.vectorstores import FAISS
from langchain_community.document_loaders import TextLoader
from langchain_text_splitters import CharacterTextSplitter

load_dotenv()


embeddings = YandexEmbeddings(folder_id=os.getenv('FOLDER_ID'), api_key=os.getenv('YANDEX_API_KEY'))
text_splitter = CharacterTextSplitter(chunk_size=2000, chunk_overlap=0)


for path in os.listdir('../files/txts'):
    txt_path = '../files/txts/'+path
    loader = TextLoader(txt_path)
    document = loader.load()
    doc = text_splitter.split_documents(document)
    db = FAISS.from_documents(doc, embeddings)
    print(db.index.ntotal)