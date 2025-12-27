import json
import os
import uuid
from flask import Flask, request, jsonify, render_template
from datetime import datetime

app = Flask(__name__)

GOOGLE_API_KEY = "AIzaSyBBJ0jNpT6u-PzXGVkx3xNbcrX9kYC-fKw"

DATA_FILE = 'trips_data.json'

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

def get_coordinates(address):
    if not address or not GOOGLE_API_KEY:
        return None, None
    
    try:
        # Google Geocoding API URL
        url = "https://maps.googleapis.com/maps/api/geocode/json"
        params = {
            "address": address,
            "key": GOOGLE_API_KEY,
            "language": "zh-TW" # 指定回傳中文結果
        }
        
        response = requests.get(url, params=params)
        data = response.json()

        if data['status'] == 'OK':
            location = data['results'][0]['geometry']['location']
            return location['lat'], location['lng']
        else:
            print(f"Google API Error: {data['status']}")
            return None, None
            
    except Exception as e:
        print(f"Geocoding Error: {e}")
        return None, None

@app.route('/')
def home():
    return render_template('index.html')

# --- API 1: 建立旅程 (Create) ---
@app.route('/api/create_trip', methods=['POST'])
def create_trip():
    try:
        meta_data = request.json
        new_id = str(uuid.uuid4())
        
        new_trip = {
            "id": new_id,
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "meta": meta_data,
            "schedule": []
        }

        all_trips = load_data()
        
        # [修改點] 改成 append，讓新資料排在最後面
        all_trips.append(new_trip) 
        
        save_data(all_trips)

        print(f"旅程已建立，ID: {new_id}")
        return jsonify({"status": "success", "trip_id": new_id}), 200

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

# --- [新增] API 1.5: 更新旅程設定 (Update Meta) ---
@app.route('/api/update_meta', methods=['POST'])
def update_meta():
    try:
        req_data = request.json
        trip_id = req_data.get('trip_id')
        new_meta = req_data.get('meta')

        all_trips = load_data()
        target_trip = next((t for t in all_trips if t['id'] == trip_id), None)

        if target_trip:
            target_trip['meta'] = new_meta # 更新基本資料
            save_data(all_trips)
            print(f"旅程 {trip_id} 基本資料已更新")
            return jsonify({"status": "success", "message": "已更新設定"}), 200
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

        # [Debug] 印出來檢查有沒有收到
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
            print(f"找不到 ID: {trip_id}")
            return jsonify({"status": "error", "message": "找不到該旅程 ID"}), 404

    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500
    
@app.route('/api/get_all_trips', methods=['GET'])
def get_all_trips():
    try:
        # 直接呼叫 load_data 讀取 json 檔案
        trips = load_data()
        return jsonify({"status": "success", "trips": trips}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)