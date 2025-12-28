import requests
import json
import time, os

BASE_DIR = os.path.dirname(__file__)
# --- 1. 設定區 ---
API_KEY = "AIzaSyBBJ0jNpT6u-PzXGVkx3xNbcrX9kYC-fKw"  # 請填入您的 Key

def get_lat_lng(location_name):
    """取得地點經緯度"""
    url = "https://maps.googleapis.com/maps/api/place/textsearch/json"
    params = {'query': location_name, 'key': API_KEY, 'language': 'zh-TW'}
    
    try:
        res = requests.get(url, params=params).json()
        if res['status'] == 'OK' and res['results']:
            loc = res['results'][0]['geometry']['location']
            print(f"📍 已定位：{location_name} ({loc['lat']}, {loc['lng']})")
            return loc['lat'], loc['lng']
    except Exception as e:
        print(f"❌ 定位錯誤: {e}")
    return None, None

def search_places(lat, lng, keyword, radius=1000):
    """搜尋單一關鍵字"""
    url = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"
    params = {
        'location': f"{lat},{lng}",
        'radius': radius,
        'keyword': keyword,
        'key': API_KEY,
        'language': 'zh-TW',
        'opennow': True
    }
    
    try:
        res = requests.get(url, params=params).json()
        results = []
        if res.get('status') == 'OK':
            for place in res.get('results', []):
                results.append({
                    "name": place.get('name'),
                    "rating": place.get('rating', 0),
                    "address": place.get('vicinity'),
                    "place_id": place.get('place_id'),
                    "types": place.get('types', [])
                })
        return results
    except Exception as e:
        print(f"❌ 搜尋錯誤 ({keyword}): {e}")
        return []

# --- 2. 主執行邏輯 ---
def main():
    # === 輸入設定 ===
    target_location = "台南火車站"          # 地點
    interests = ["拉麵", "咖啡廳", "書店"]   # 興趣列表
    radius = 800                          # 半徑 (公尺)
    # ===============

    print(f"🚀 開始搜尋：{target_location} 附近的 {interests}")

    # 步驟 1: 取得座標
    lat, lng = get_lat_lng(target_location)
    if not lat:
        print("無法找到地點，程式結束。")
        return

    # 步驟 2: 迴圈搜尋並合併結果
    all_results = []
    seen_ids = set()  # 用來去重 (避免同一家店重複出現)

    for interest in interests:
        print(f"🔍 正在搜尋：{interest}...")
        shops = search_places(lat, lng, interest, radius)
        
        for shop in shops:
            if shop['place_id'] not in seen_ids:
                shop['tag'] = interest # 標記這是因為搜什麼字找到的
                all_results.append(shop)
                seen_ids.add(shop['place_id'])
        
        time.sleep(1) # 避免呼叫過快

    # 步驟 3: 儲存成 data.json
    output_data = {
        "search_target": target_location,
        "search_radius": radius,
        "coordinates": {"lat": lat, "lng": lng},
        "total_found": len(all_results),
        "results": all_results
    }

    data_path = os.path.join(BASE_DIR, "json", "data.json")
    with open(data_path, "w", encoding="utf-8") as f:
        json.dump(output_data, f, ensure_ascii=False, indent=4)

    print(f"✅ 完成！共找到 {len(all_results)} 筆資料，已儲存至 'result.json'")

if __name__ == "__main__":
    main()