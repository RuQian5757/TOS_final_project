import json
import os
import uuid
import requests 
from flask import Flask, request, jsonify, render_template, Response
from datetime import datetime
from tools import *
from google import create_data_json, fetch_static_map_image

app = Flask(__name__)

GOOGLE_API_KEY = "AIzaSyBBJ0jNpT6u-PzXGVkx3xNbcrX9kYC-fKw" 

BASE_DIR = os.path.dirname(__file__)
DATA_FILE = os.path.join(BASE_DIR, 'json', 'trips_data.json')
REQUEST_FILE = os.path.join(BASE_DIR, 'json', 'request.json') 
RESPONSE_FILE = os.path.join(BASE_DIR, 'json', 'options.json') 

# --- 資料讀寫輔助函式 ---
def load_data():
    if not os.path.exists(DATA_FILE):
        return []
    try:
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return []

def save_data(data):
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

# --- Google Maps Geocoding 查詢函式 ---
def get_coordinates(address):
    if not address:
        print("❌ 錯誤：地址是空的")
        return None, None
    # 簡單防呆，避免使用預設字串
    if "YOUR_GOOGLE_API_KEY" in GOOGLE_API_KEY:
        print("❌ 錯誤：請設定真實的 Google API Key")
        return None, None
    
    try:
        url = "https://maps.googleapis.com/maps/api/geocode/json"
        params = {
            "address": address,
            "key": GOOGLE_API_KEY,
            "language": "zh-TW"
        }
        
        response = requests.get(url, params=params)
        data = response.json()

        if data['status'] == 'OK':
            location = data['results'][0]['geometry']['location']
            return location['lat'], location['lng']
        else:
            print(f"❌ Google API Error: {data['status']}")
            return None, None
            
    except Exception as e:
        print(f"❌ Geocoding Error: {e}")
        return None, None

# --- 首頁路由 ---
@app.route('/')
def home():
    return render_template('index.html')

# --- API 1: 建立旅程 (Create) ---
@app.route('/api/create_trip', methods=['POST'])
def create_trip():
    try:
        meta_data = request.json
        new_id = str(uuid.uuid4())
        
        address = meta_data.get('location')
        print(f"正在查詢地點座標: {address}...")
        lat, lng = get_coordinates(address)
        
        meta_data['lat'] = lat
        meta_data['lng'] = lng
        
        new_trip = {
            "id": new_id,
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "meta": meta_data,
            "schedule": []
        }

        all_trips = load_data()
        all_trips.append(new_trip)
        save_data(all_trips)

        print(f"旅程已建立，ID: {new_id}，座標: {lat}, {lng}")
        
        return jsonify({
            "status": "success", 
            "trip_id": new_id,
            "start_point": {"lat": lat, "lng": lng}
        }), 200

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

# --- API 1.5: 更新旅程設定 (Update Meta) ---
@app.route('/api/update_meta', methods=['POST'])
def update_meta():
    try:
        req_data = request.json
        trip_id = req_data.get('trip_id')
        new_meta = req_data.get('meta')

        all_trips = load_data()
        target_trip = next((t for t in all_trips if t['id'] == trip_id), None)

        if target_trip:
            old_location = target_trip['meta'].get('location')
            new_location = new_meta.get('location')
            
            lat, lng = None, None
            
            if old_location != new_location:
                print(f"地點變更 ({old_location} -> {new_location})，重新查詢座標...")
                lat, lng = get_coordinates(new_location)
                new_meta['lat'] = lat
                new_meta['lng'] = lng
            else:
                lat = target_trip['meta'].get('lat')
                lng = target_trip['meta'].get('lng')
                new_meta['lat'] = lat
                new_meta['lng'] = lng

            target_trip['meta'] = new_meta
            save_data(all_trips)
            
            return jsonify({
                "status": "success", 
                "message": "已更新設定",
                "start_point": {"lat": lat, "lng": lng}
            }), 200
        else:
            return jsonify({"status": "error", "message": "ID 不存在"}), 404
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

# --- API 2: 新增行程項目 (Add Item) ---
@app.route('/api/add_item', methods=['POST'])
def add_item():
    try:
        req_data = request.json
        trip_id = req_data.get('trip_id')
        new_item = req_data.get('item')

        print(f"嘗試新增項目: ID={trip_id}, Item={new_item.get('place_name')}")

        if not trip_id:
            return jsonify({"status": "error", "message": "前端未傳送 ID"}), 400

        all_trips = load_data()
        target_trip = next((t for t in all_trips if t['id'] == trip_id), None)
        
        if target_trip:
            target_trip['schedule'].append(new_item)
            save_data(all_trips)
            return jsonify({"status": "success", "message": "項目已新增"}), 200
        else:
            return jsonify({"status": "error", "message": "找不到該旅程 ID"}), 404

    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

# --- API 3: 取得所有行程 (Get All) ---
@app.route('/api/get_all_trips', methods=['GET'])
def get_all_trips():
    try:
        trips = load_data()
        return jsonify({"status": "success", "trips": trips}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

# --- [修正] API 4: 儲存需求為 request.json ---
@app.route('/api/generate_ai_prompt', methods=['POST'])
def generate_ai_prompt():
    try:
        req_data = request.json
        
        with open(REQUEST_FILE, 'w', encoding='utf-8') as f:
            json.dump(req_data, f, ensure_ascii=False, indent=4)
        
        print(f"✅ 已將原始需求儲存至 {REQUEST_FILE}")

        # call key AI to get 3 keys for google api
        key_list = generate_keys()
        print("Key AI complete !!!")

        # call google api to create data.json aka shops in certain radius
        create_data_json(key_list)
        print("Google search complete !!!")
        # call guide RAG AI to create options.json 
        generate_options_json()
        print("RAG AI complete")


        return jsonify({
            "status": "success", 
            "message": "資料已儲存",
            "saved_data": req_data 
        }), 200

    except Exception as e:
        print(f"❌ Error saving request json: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500
    
@app.route('/api/regenerate_ai_prompt', methods=['POST'])
def regenerate_ai_prompt():
    try:
        req_data = request.json
        
        with open(REQUEST_FILE, 'w', encoding='utf-8') as f:
            json.dump(req_data, f, ensure_ascii=False, indent=4)
            
        print(f"✅ 已將原始需求儲存至 {REQUEST_FILE}")

        # regenerate
        generate_options_json()

        return jsonify({
            "status": "success", 
            "message": "資料已儲存",
            "saved_data": req_data 
        }), 200

    except Exception as e:
        print(f"❌ Error saving request json: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500
    
@app.route('/api/get_ai_options', methods=['GET'])
def get_ai_options():
    try:
        if not os.path.exists(RESPONSE_FILE):
            return jsonify({"status": "waiting", "message": "AI genetating..."}), 404
        with open(RESPONSE_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # delete options.json
        # os.remove(RESPONSE_FILE)

        return jsonify({"status": "success", "options": data}), 200
    
    except Exception as e:
        print(f"❌ Error reading options.json: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500
    
@app.route('/api/map_image')
def get_map_image():
    try:
        lat = request.args.get('lat')
        lng = request.args.get('lng')

        image_content = fetch_static_map_image(lat, lng)

        if image_content:
            return Response(image_content, mimetype='image/png')
        else:
            return "Image generation failed", 400
    
    except Exception as e:
        print(f"Proxy Error: {e}")
        return "Error fetching map", 500


if __name__ == '__main__':
    app.run(debug=True, port=5000)