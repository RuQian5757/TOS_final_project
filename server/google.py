import requests
import json
import time, os, re

BASE_DIR = os.path.dirname(__file__)
# --- 1. 設定區 ---
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

def get_lat_lng(location_name):
    """取得地點經緯度"""
    url = "https://maps.googleapis.com/maps/api/place/textsearch/json"
    params = {'query': location_name, 'key': GOOGLE_API_KEY, 'language': 'zh-TW'}
    
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
        'key': GOOGLE_API_KEY,
        'language': 'zh-TW',
        'opennow': True
    }
    
    try:
        res = requests.get(url, params=params).json()
        if res.get('status') == 'OK':
            return res
    except Exception as e:
        print(f"❌ 搜尋錯誤 ({keyword}): {e}")
        return []

def create_data_json(keys_list):
    req_path = os.path.join(BASE_DIR, 'json', 'request.json')
    with open(req_path, "r", encoding='utf-8') as f:
        req_data = json.load(f)
    
    lat = req_data['coordinates'].get('lat', 0.0)
    lng = req_data['coordinates'].get('lng', 0.0)

    max_travel_distance = req_data.get('max_travel_distance', "1 km")
    radius = int (1000 * float(re.search(r"[\d.]+", max_travel_distance).group()))

    merged_shops = {
        "html_attributions": [],
        "results": [],
        "status": "OK"
    }

    for key in keys_list:
        print(f"🔍 正在搜尋：{key}...")
        shops = search_places(lat, lng, key, radius)
        
        # 合併 html_attributions
        merged_shops["html_attributions"].extend(shops.get("html_attributions", []))
        
        # 合併 results
        merged_shops["results"].extend(shops.get("results", []))
        
        # merged_shops["status"] = shops.get("status", "OK")
        
        time.sleep(1) 

    data_path = os.path.join(BASE_DIR, "json", "data.json")
    with open(data_path, "w", encoding="utf-8") as f:
        json.dump(merged_shops, f, ensure_ascii=False, indent=4)

    print(f"✅ 完成！共找到 {len(merged_shops)} 筆資料，已儲存至 'data.json'")

def fetch_static_map_image(lat, lng):
    """
    接收經緯度，向 Google Maps Static API 請求圖片，
    並回傳圖片的二進位資料 (bytes)。
    """
    if not lat or not lng:
        return None

    try:
        zoom = 15
        size = "600x400"
        
        google_url = (
            f"https://maps.googleapis.com/maps/api/staticmap?"
            f"center={lat},{lng}&"
            f"zoom={zoom}&"
            f"size={size}&"
            f"maptype=roadmap&"
            f"markers=color:red%7C{lat},{lng}&"
            f"key={GOOGLE_API_KEY}"
        )
        
        response = requests.get(google_url)
        
        if response.status_code == 200:
            return response.content 
        else:
            print(f"❌ Google Map API Error: {response.status_code} - {response.text}")
            return None

    except Exception as e:
        print(f"❌ Fetch Map Error: {e}")
        return None