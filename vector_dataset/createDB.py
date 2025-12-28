import os
from langchain_community.document_loaders import TextLoader, PyPDFLoader, UnstructuredWordDocumentLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.embeddings import HuggingFaceEmbeddings
from huggingface_hub import login
from langchain_community.vectorstores import FAISS

""" 載入檔案

將放在 ./uploaded_files 中的檔案載入，並將其讀成documents
"""
BASE_DIR = os.path.dirname(__file__)


folder_path = os.path.join(BASE_DIR, 'uploaded_files')
documents = []
 
if not os.path.exists(folder_path):
    raise RuntimeError(f"{folder_path} not found")

for file in os.listdir(folder_path):
    path = os.path.join(folder_path, file)

    if file.endswith(".txt"):
        print(f"📄 正在導入 TXT：{file}")
        loader = TextLoader(path, encoding="utf-8")
    elif file.endswith(".pdf"):
        print(f"📕 正在導入 PDF：{file}")
        loader = PyPDFLoader(path)
    elif file.endswith(".docx"):
        print(f"📝 正在導入 DOCX：{file}")
        loader = UnstructuredWordDocumentLoader(path)
    else:
        continue

    documents.extend(loader.load())


"""切分文件
將檔案文件內容依照chunk_size做切分，並設置chunk_overlap保留上下文關係
"""

splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=100)
split_docs = splitter.split_documents(documents)

print(f"Loaded {len(documents)} documents")
print(f"Split into {len(split_docs)} chunks")

"""向量模型
使用 HuggingFace 的 embeddinggemma-300m 模型產生向量

"""

class EmbeddingGemmaEmbeddings(HuggingFaceEmbeddings):
    def __init__(self, **kwargs):
        super().__init__(
            model_name="google/embeddinggemma-300m",        # HF 上的官方模型
            encode_kwargs={"normalize_embeddings": True},   # 一般檢索慣例
            **kwargs
        )

    # embed成官方建議的前綴
    def embed_documents(self, texts):
        texts = [f'title: none | text: {t}' for t in texts]
        return super().embed_documents(texts)

    def embed_query(self, text):
        return super().embed_query(f'task: search result | query: {text}')

"""登入Huggin Face
須至 https://huggingface.co/ 創建帳號，並前往setting/access token頁面
按下Create new Token，Token Type 為 Read，將token設置道環境變數中
登入後才可以將 embedding model 建立起來
"""

HF_TOKEN = os.environ.get("HUGGING_FACE_TOKEN")
if not HF_TOKEN:
    raise RuntimeError("HUGGING_FACE_TOKEN not set")

login(token=HF_TOKEN)


# 建立向量資料庫


embedding_model = EmbeddingGemmaEmbeddings()
vectorstore = FAISS.from_documents(split_docs, embedding_model)

# 儲存向量資料庫
vectorstore.save_local("faiss_db")