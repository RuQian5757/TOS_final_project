import os, json
import textwrap, re
from haversine import haversine, Unit

BASE_DIR = os.path.dirname(__file__)

def parese_options_prompt(additional_prompt: str, target: str) -> str:
    """
    從 data.json 讀取餐廳資訊，生成 prompt 並加上額外的字串。
    """
    final_prompt = textwrap.dedent(f"""
            我這次旅遊一起的對象是：{target}
            並且我希望這些地點能滿足這些需求「{additional_prompt}」
        """)

    # 取得目前檔案所在路徑
    data_path = os.path.join(BASE_DIR, "json", "data.json")

    # 讀取 JSON
    with open(data_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    results = data.get("results", [])


    # 生成餐廳資訊文字
    prompt_list = "請幫我從以下的店家去做選擇，篩選出5間符合我需求的地點\n"
    i = 0
    for r in results:
        name = r.get("name", "未知名稱")
        address = r.get("vicinity", "未知地址")
        rating = r.get("rating", "未知評分")

        i += 1
        prompt_list += textwrap.dedent(f"""
                第{i}家店：

                地點名稱：{name}
                地址：{address}
                評分：{rating}
                """)

    # 加上額外的 prompt
    final_prompt += "\n" + prompt_list

    return final_prompt

def parese_tag_prompt(additional_prompt: str, type: str) -> str:
    final_prompt = textwrap.dedent(f"""
            我目前想要找的地點類型是{type}            
            我得需求是「{additional_prompt}」

            關鍵字也就是更詳細的地點敘述
            請生成三個個別約10字以內的關鍵字，猜測我想要去的地點，關鍵字就例如:小吃店、名勝古蹟、公園等
        """)
    return final_prompt

def parse_rag_output(rag_text: str):
    """
    解析 RAG 回傳的文字，生成符合 options.json 的 list
    """
    options = []
    
    data_path = os.path.join(BASE_DIR, "json", "data.json")
    with open(data_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    req_path = os.path.join(BASE_DIR, "json", "request.json")
    with open(req_path, "r", encoding="utf-8") as f:
        req_data = json.load(f)

    # 將每個推薦地點切分出來
    # 每個推薦地點之間都有 "---------" 分隔
    places = re.split(r'-{5,}', rag_text)

    for place_text in places:
        # 忽略空字串
        if not place_text.strip():
            continue
        # print(place_text)
        # print("-------------------")

        # 解析地點名稱
        name_match = re.search(r'地點名稱\s*[:：]\s*(.+)', place_text)
        name = name_match.group(1).strip() if name_match else ""
        
        # 解析評分
        rating_match = re.search(r'評分\s*[:：]\s*([0-9.]+)', place_text)
        rating = float(rating_match.group(1)) if rating_match else 0.0

        # 解析推薦文
        reason_match = re.search(r'推薦文\s*[:：]\s*(.+)', place_text)
        ai_reason = reason_match.group(1).strip() if reason_match else ""

        # 解析 tags，轉成 list
        tags_match = re.search(r'tags\s*[:：]\s*(.+)', place_text, re.IGNORECASE)
        tags = (
            [t.strip() for t in re.split(r'[、,]', tags_match.group(1))]
            if tags_match else []
        )
        print(tags_match)
        print(tags)
        print("=====================")
        # 取得time_slot
        time_slot = req_data["time_slot"]

        # 取得類型

        # 取得lat, lng
        lat = 0.0
        lng = 0.0
        for place in data.get('results', []):
            place_name = place.get('name', "")
            if name in place_name or place_name in name:
                location = place.get('geometry', {}).get('location', {})
                lat = location.get('lat', "")
                lng = location.get('lng', "")
                break

        # 計算距離
        start_lat = req_data['coordinates'].get('lat', 0.0)
        start_lng = req_data['coordinates'].get('lng', 0.0)

        point1 = (start_lat, start_lng)
        point2 = (lat, lng)

        distance = haversine(point1, point2, unit=Unit.KILOMETERS)

        distance_info = f"{distance:.2f} km"

        # 組成 options dict
        option = {
            "place_name": name,
            "category": "美食",          # 預設填美食
            "time_range": req_data["time_slot"],   # 預設時間區段
            "rating": rating,
            "tags": tags,
            "ai_reason": ai_reason,
            "distance_info": distance_info,
            "lat": lat,
            "lng": lng
        }

        options.append(option)

    return options

def parse_key_output(key_text: str) -> list:
   key_text = key_text.strip('"')
   place_list = [x.strip() for x in key_text.split(',')]
   return place_list 