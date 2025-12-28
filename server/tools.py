from llm_client import call_RAG_llm, call_key_llm
from parsing import *
import os, json

key_model = "gemma3:4b"
rag_model = "gpt-oss:120b"
# rag_model = "gemma3:4b"
BASE_DIR = os.path.dirname(__file__)

def generate_keys() -> list:
    """
    產生關鍵字
    
    根據接收使用者的請求內容，透過key AI產生該地點的三個關鍵字
    
    Returns:
        list: 三個關鍵字
    """
    req_path = os.path.join(BASE_DIR, "json", "request.json")

    with open(req_path, "r", encoding="utf-8") as f:
        req_data = json.load(f)

    # 取出你要的欄位
    prompt = req_data.get("prompt", "")
    type = req_data.get("category_selection", "")
    keys_reply = call_key_llm(key_model, parse_key_prompt(prompt, type))

    keys_list = parse_key_output(keys_reply)

    return keys_list

def generate_options_json():
    """
    根據接收使用者的請求prompt以及旅遊對象，呼叫RAG AI產生五個選項\n
    並將選項儲存到options.json中
    """
    req_path = os.path.join(BASE_DIR, "json", "request.json")

    with open(req_path, "r", encoding="utf-8") as f:
        req_data = json.load(f) 

    prompt = req_data.get("prompt", "")      
    target = req_data.get("companion", "")    

    reply = call_RAG_llm(rag_model, parse_options_prompt(prompt, target))

    # print("------------------")
    # print("Reply of RAG AI: ")
    # print(reply)
    # print("------------------")

    options = parse_rag_output(reply)

    options_path = os.path.join(BASE_DIR, "json", "options.json")
    with open(options_path, "w", encoding="utf-8") as f:
        json.dump(options, f, ensure_ascii=False, indent=4)

    return