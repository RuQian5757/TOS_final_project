
# llm_client.py
import requests
import os
import json
import textwrap
from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import HuggingFaceEmbeddings
from parsing import parese_tag_prompt


print("llm_client.py Initializing ...")
BASE_DIR = os.path.dirname(__file__)
BASE_URL = "https://api-gateway.netdb.csie.ncku.edu.tw"
ENDPOINT = "/api/chat"

API_KEY = os.environ.get("LLM_API_KEY")

# --- 內部對話歷史，自動初始化 ---
_history = []

# 可調整保留最近幾輪對話
MAX_HISTORY = 10

"""向量模型
透過google/embeddinggemma-300m的embedding model，幫忙解析faiss_db內容，以及做查詢
"""

class EmbeddingGemmaEmbeddings(HuggingFaceEmbeddings):
    def __init__(self, **kwargs):
        super().__init__(
            model_name="google/embeddinggemma-300m",
            encode_kwargs={"normalize_embeddings": True},
            **kwargs
        )

    def embed_documents(self, texts):
        texts = [f"title: none | text: {t}" for t in texts]
        return super().embed_documents(texts)

    def embed_query(self, text):
        return super().embed_query(f"task: search result | query: {text}")

faiss_path = os.path.join(BASE_DIR, "vector_dataset", "faiss_db")

embedding_model = EmbeddingGemmaEmbeddings()
vectorstore = FAISS.load_local(
    faiss_path,
    embeddings=embedding_model,
    allow_dangerous_deserialization=True
)
retriever = vectorstore.as_retriever(search_kwargs={"k": 4})    #每次檢索 4 個相關段落

def retrieve_context(user_input: str) -> str:
    """
    從 FAISS 資料庫檢索最相關的段落
    """
    docs = retriever.invoke(user_input)
    retrieved_chunks = "\n\n".join([doc.page_content for doc in docs])
    return retrieved_chunks

def call_RAG_llm(model: str, user_prompt: str) -> str:
    """
    Call LLM chat API with automatic assistant history management.

    :param model: model name, e.g. "llama3.1:70b"
    :param prompt: user prompt
    :return: assistant reply text
    """
    global _history  # 使用 module 內部 history

    system_prompt = textwrap.dedent("""
        你是一位資深的導遊，熟知台灣各處的美食、景點與娛樂
        能夠依照使用者不同的需求，推薦恰當且人性化的地點選擇
        
        你的任務是「根據使用者告訴的地點、旅遊對象以及需求，從中挑選出5個較適合的地點選項，並針對每個地點提供簡短30字的推薦文以及兩個tags，可透過參考資料或上網搜尋」
        推薦文請以資深導遊的口吻來做描述，引發使用者的興趣，感受到是真心推薦給他的地點
        tags請以資深導遊分析這個地方的屬性，提供三個一些該地點的專屬標籤，例如:牛肉麵、老店、親子、打卡等簡單幾個字的文字敘述
        同時，若過去你已推薦過使用者該地點，則必須從使用者所給的地點中，挑選出新的且不重複的地點
                             
        請嚴格依照回覆格式做回應
                             
        回覆格式：
        1. 內容要包含地點名稱、地址、評分、推薦文、tags
        2. 每個推薦選項要用 --------- 做區隔
        3. 要以列點的方式輸出
        4. 不要將你的判斷文字輸出出來，只能有像是範例輸出的格式
        5. 不要吃現Provide format.或是We need to browse的文字輸出
        6. 請使用半形的冒號，必且在冒號前後都有一個空格
        7. tags僅能有最多3個，並且文字中不要有 etc. 之類的而外文字出現
        8. 務必反覆確認該地點名稱與使用者給的地點名稱是相符的，不要自己創造新的地點名稱
        9. 請從使用者傳的「請幫我從以下的店家去做選擇」之後的「第x家店：」，去做推薦哪間店的判斷
        10.tags在不同地點的標籤盡可能做出差異性，針對該地點的屬性去做判斷，例如:老店、當地必吃、網友熱推、觀光勝地等屬性的tags
                                                           
        範例輸出：
        推薦地點1:
            地點名稱 : xx飯館
            地址 : xx路x段xxx號
            評分 : 4.2
            推薦文 : 湯頭清甜濃郁、牛肉鮮嫩不柴，現沖現喝最對味，在地人與觀光客必吃的台南經典美食
            tags : 百年老店、在地美食
        ---------
        推薦地點2:
            地點名稱 : xx古蹟
            地址 : xx路x段xxx號
            評分 : 4.2
            推薦文 : 走進百年古蹟，紅磚歲月低語歷史，文化底蘊深厚，值得細細品味吧
            tags : 名勝古蹟、打卡勝地
        ---------
        ...            
        """)

    url = BASE_URL + ENDPOINT
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }

    # 建立 messages
    messages = []
    # 加入system prompt
    messages.append({"role": "system", "content": system_prompt})

    # 加入歷史對話，保留最後 MAX_HISTORY 輪
    if _history:
        history = _history[-MAX_HISTORY*2:]  # 每輪包含 user + assistant
        messages.extend(history)

    # 加入本輪 user prompt
    # 先用 FAISS 取回相關資料
    retrieved_context = retrieve_context(user_prompt)

    # 將檢索結果整合到 prompt
    final_prompt = f"根據下列資料：\n{retrieved_context}\n\n回答使用者的問題：{user_prompt}\n若無法回答則請自行上網查找資料。"

    messages.append({"role": "user", "content": final_prompt})

    # print("------------------")
    # print("Prompt of RAG AI: ")
    # print(final_prompt)
    # print("------------------")

    # payload
    payload = {
        "model": model,
        "messages": messages,
        "stream": False,            #是否串流回傳 token
        "temperature": 0.6,         #創意度，越高回答越自由
        "top_p": 0.9,
        "max_tokens": 100,          #最大回傳長度
        # "stop": ["\n"],           #停止符號列表，遇到就停止
        "presence_penalty": 0.4,    #鼓勵 AI 提及新話題
        "frequency_penalty": 0.8,   #減少重複
        # "user": "student001"      #設定使用者 ID
    }

    response = requests.post(url, headers=headers, json=payload)

    if response.status_code != 200:
        raise RuntimeError(
            f"LLM API failed ({response.status_code}): {response.text}"
        )

    data = response.json()

    # 儲存本輪 JSON
    json_path = os.path.join(BASE_DIR, "json", "RAG_LLM_reply.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

    # 取得 assistant 回覆
    reply = data["message"]["content"]

    # 將本輪對話加入 history
    _history.append({"role": "user", "content": final_prompt})
    _history.append({"role": "assistant", "content": reply})

    return reply

def call_key_llm(model: str, user_prompt: str, type: str) -> str:
    """
    Call LLM chat API.

    :param model: model name, e.g. "llama3.1:70b"
    :param prompt: user prompt
    :return: assistant reply text
    """
    system_prompt = textwrap.dedent("""
        你是一位心理洞察師，你能從文字中清楚知道使用者實際在想什麼
        對於模糊的敘述，都能給出精準的猜測，讓使用者知道他要什麼
        所以你的任務是「根據使用者的文字與地點類型，給出合適的地點關鍵字，同時每個關鍵字限制在10字以內」
        關鍵字也就是更詳細的地點類型敘述，例如：古蹟、小吃店、遊樂園
                            
        請嚴格依照回覆格式做回應
                            
        回覆格式:
        1 .將每個關鍵字以逗號做區隔，並寫在同一行
        2. 只產生三個關鍵字
                                    
        範例：
        "關鍵字1, 關鍵字2, 關鍵字3" 
    """)

    url = BASE_URL + ENDPOINT
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }

    final_prompt = textwrap.dedent(f"""
            我的地點類型是:{type}
            我的需求是:{user_prompt}
        """)
    
    # 建立 messages
    messages = []
    # 加入system prompt
    messages.append({"role": "system", "content": system_prompt})
    # 加入 user prompt
    messages.append({"role": "user", "content": final_prompt})

    # print("------------------")
    # print("Prompt of key AI: ")
    # print(final_prompt)
    # print("------------------")

    # payload
    payload = {
        "model": model,
        "messages": messages,
        "stream": False,            #是否串流回傳 token
        "temperature": 0.5,         #創意度，越高回答越自由
        "top_p": 0.9,
        "max_tokens": 100,          #最大回傳長度
        # "stop": ["\n"],           #停止符號列表，遇到就停止
        "presence_penalty": 0.4,    #鼓勵 AI 提及新話題
        "frequency_penalty": 0.7,   #減少重複
        # "user": "student001"      #設定使用者 ID
    }

    response = requests.post(url, headers=headers, json=payload)

    if response.status_code != 200:
        raise RuntimeError(
            f"LLM API failed ({response.status_code}): {response.text}"
        )

    data = response.json()

    # 儲存本輪 JSON
    json_path = os.path.join(BASE_DIR, "json", "tag_LLM_reply.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

    # 取得 assistant 回覆
    reply = data["message"]["content"]

    return reply


print("llm_client.py Initialization finished ")