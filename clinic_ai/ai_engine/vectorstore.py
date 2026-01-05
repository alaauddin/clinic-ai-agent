from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyPDFLoader, TextLoader, DirectoryLoader
from django.conf import settings
import os

class ClinicVectorStore:
    def __init__(self):
        # Using langchain-huggingface to avoid deprecation warnings
        # explicitly setting device to cpu to avoid meta tensor issues
        self.embeddings = HuggingFaceEmbeddings(
            model_name="sentence-transformers/all-MiniLM-L6-v2",
            model_kwargs={'device': 'cpu'},
            encode_kwargs={'normalize_embeddings': True}
        )
        self.vector_db = None
        self.index_path = settings.FAISS_INDEX_PATH
        self.docs_path = settings.DOCS_DIR

    def load_index(self):
        index_file = os.path.join(self.index_path, "index.faiss")
        if os.path.exists(index_file):
            try:
                self.vector_db = FAISS.load_local(
                    str(self.index_path), 
                    self.embeddings, 
                    allow_dangerous_deserialization=True
                )
                return True
            except Exception as e:
                print(f"Error loading FAISS index: {e}")
                return False
        return False

    def build_index(self):
        if not os.path.exists(self.docs_path):
            os.makedirs(self.docs_path)
            
        # Ensure at least one file exists
        welcome_file = os.path.join(self.docs_path, "welcome.txt")
        if not os.listdir(self.docs_path):
            with open(welcome_file, "w", encoding='utf-8') as f:
                f.write("مرحباً بكم في العيادة. نحن نقدم أفضل الخدمات الطبية.")

        loaders = [
            DirectoryLoader(str(self.docs_path), glob="*.txt", loader_cls=TextLoader),
            DirectoryLoader(str(self.docs_path), glob="*.pdf", loader_cls=PyPDFLoader),
        ]
        
        docs = []
        for loader in loaders:
            try:
                docs.extend(loader.load())
            except Exception as e:
                print(f"Error loading from {loader}: {e}")

        if not docs:
            return False

        text_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
        splits = text_splitter.split_documents(docs)

        self.vector_db = FAISS.from_documents(splits, self.embeddings)
        
        if not os.path.exists(self.index_path):
            os.makedirs(self.index_path)
            
        self.vector_db.save_local(str(self.index_path))
        return True

    def get_retriever(self):
        if self.vector_db is None:
            if not self.load_index():
                self.build_index()
        
        if self.vector_db is None:
            # Fallback if building also fails for some reason
            raise Exception("Failed to initialize vector database.")
            
        return self.vector_db.as_retriever(search_kwargs={"k": 6})
