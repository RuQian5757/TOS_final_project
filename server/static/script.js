// --- Global State ---
let navigationStack = ['step-home']; 

let itineraryItems = []; // 前端暫存的行程列表
let currentPendingItem = null; // 當前選擇的項目
let savedTrips = []; // 歷史紀錄 (從後端抓取)
let savedFavorites = []; 
let currentViewingTripId = null;
let isInstantMode = false; 
let activeServerTripId = null; // 用來儲存後端回傳的 ID
let aiGeneratedOptions = null;

let tripSettings = { 
    tripName: '', 
    location: '台南', 
    date: '2025/10/20',
    companion: '情侶', 
    transport: '機車',
    lat: null, 
    lng: null  
}; 

const mockOptions = [
    { id: 1, name: "文章牛肉湯", type: "美食", rating: 4.8, tags: ["排隊名店"], reason: "經典台南早餐，距離近。", distance: "1.2 km", lat: 22.9985, lng: 120.2130 },
    { id: 2, name: "臺南市美術館 2 館", type: "景點", rating: 4.6, tags: ["冷氣超強", "拍照"], reason: "建築特色美，適合避暑。", distance: "1.5 km", lat: 22.9900, lng: 120.2000 },
    { id: 3, name: "林百貨", type: "購物", rating: 4.5, tags: ["古蹟"], reason: "文創商品豐富。", distance: "0.9 km", lat: 22.9930, lng: 120.2050 },
    { id: 4, name: "安平古堡", type: "景點", rating: 4.4, tags: ["歷史", "戶外"], reason: "體驗荷蘭時期的歷史風情。", distance: "3.0 km", lat: 23.0010, lng: 120.1610 }
];

// --- Initialization ---
document.addEventListener('DOMContentLoaded', () => {
    const tags = document.querySelectorAll('.tag-btn');
    tags.forEach(btn => {
        btn.addEventListener('click', () => {
            tags.forEach(b => {
                b.classList.remove('bg-blue-100', 'text-blue-600', 'border-blue-200');
                b.classList.add('bg-gray-100', 'text-gray-600');
            });

            btn.classList.remove('bg-gray-100', 'text-gray-600');
            btn.classList.add('bg-blue-100', 'text-blue-600', 'border-blue-200');
        });
    });

    const nameInput = document.getElementById('detail-trip-name');
    if(nameInput) {
        nameInput.addEventListener('input', (e) => {
            if(currentViewingTripId) {
                const trip = savedTrips.find(t => t.id === currentViewingTripId);
                if(trip) trip.meta.trip_name = e.target.value;
            }
        });
    }
});

// --- Smart Navigation Logic ---
function goToStep(stepId) {
    let targetId = stepId;
    if (typeof stepId === 'number') targetId = `step-${stepId}`;
    else if (stepId === 'home') targetId = 'step-home';
    else if (stepId === 'plan-setup') targetId = 'step-plan-setup';
    else if (stepId === 'dashboard') targetId = 'step-dashboard';
    else if (stepId === 'trip-detail') targetId = 'step-trip-detail';

    navigationStack.push(targetId);
    _showStep(targetId);
}

function goBack() {
    if (navigationStack.length > 1) {
        navigationStack.pop();
        const previousStepId = navigationStack[navigationStack.length - 1];
        _showStep(previousStepId);
    } else {
        _showStep('step-home');
        navigationStack = ['step-home'];
    }
}

function _showStep(targetId) {
    document.querySelectorAll('.step-section').forEach(el => el.classList.remove('active'));
    let targetEl = document.getElementById(targetId);
    if (!targetEl) {
        targetId = 'step-home';
        targetEl = document.getElementById(targetId);
        navigationStack = ['step-home'];
    }
    if(targetEl) {
        targetEl.classList.add('active');
        window.scrollTo(0, 0);
    }
    if(targetId === 'step-home') updateBottomNavState('home');
    if(targetId === 'step-3') renderOptions();
    if(targetId === 'step-4') renderStep4Buttons(); 
}

// --- Mode Logic ---
function startInstantMode() { 
    isInstantMode = true;
    goToStep(2); 
}

function startPlanningMode() { 
    document.querySelectorAll('.tag-btn').forEach(btn => {
        btn.classList.remove('bg-blue-100', 'text-blue-600', 'border-blue-200');
        btn.classList.add('bg-gray-100', 'text-gray-600');
    });
    const txtArea = document.querySelector('textarea');
    if(txtArea) txtArea.value = '';
    const nameInput = document.getElementById('tripNameInput');
    if(nameInput) nameInput.value = '';
    const locInput = document.getElementById('locationInput');
    if(locInput) locInput.value = '';

    const startTimeEl = document.getElementById('blockStartTime');
    const endTimeEl = document.getElementById('blockEndTime');
    if(startTimeEl) startTimeEl.value = "10:00";
    if(endTimeEl) endTimeEl.value = "12:00";
    
    const distanceInput = document.querySelector('input[type="range"]');
    if(distanceInput) distanceInput.value = 5;

    isInstantMode = false;
    goToStep('plan-setup'); 
}

// Get user location
function getCurrentLocation() {
    return new Promise((resolve, reject) => {
        if(!navigator.geolocation) {
            reject(new Error("您的瀏覽器不支援地理定位功能。"));
        }
        else {
            navigator.geolocation.getCurrentPosition(
                (position) => {
                    resolve({
                        lat: position.coords.latitude, 
                        lng: position.coords.longitude 
                    });
                },
                (error) => {
                    reject(error);
                }
            );
        }
    });
}

// --- [核心] Step 1: 初始化並傳送 Meta ---
async function initializeAndGoToDashboard() {
    const nameInput = document.getElementById('tripNameInput').value;
    const locInput = document.getElementById('locationInput').value;
    const dateInput = document.getElementById('dateInput').value;
    const companionInput = document.getElementById('companionInput').value;
    const transportInput = document.getElementById('transportInput').value;

    if(locInput) tripSettings.location = locInput;
    if(dateInput) tripSettings.date = dateInput;
    if(companionInput) tripSettings.companion = companionInput;
    if(transportInput) tripSettings.transport = transportInput;
    
    tripSettings.tripName = nameInput.trim() || `${tripSettings.location}之旅`;
    
    const metaPayload = {
        trip_name: tripSettings.tripName,
        location: tripSettings.location,
        date: tripSettings.date,
        companion: tripSettings.companion,
        transport: tripSettings.transport
    };

    try {
        if (!activeServerTripId) {
            // 新旅程：呼叫 create_trip
            const response = await fetch('/api/create_trip', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(metaPayload)
            });
            const result = await response.json();
            
            if(response.ok) {
                console.log("Server 初始化成功，ID:", result.trip_id);
                activeServerTripId = result.trip_id; 
                
                // [儲存起始點座標]
                if(result.start_point) {
                    tripSettings.lat = result.start_point.lat;
                    tripSettings.lng = result.start_point.lng;
                    console.log("已記錄起始座標:", tripSettings.lat, tripSettings.lng);
                }
                itineraryItems = []; 
            }
        } else {
            // 舊旅程：呼叫 update_meta
            const response = await fetch('/api/update_meta', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    trip_id: activeServerTripId,
                    meta: metaPayload
                })
            });
            const result = await response.json();
            
            // [更新座標]
            if(result.start_point) {
                tripSettings.lat = result.start_point.lat;
                tripSettings.lng = result.start_point.lng;
            }
        }
    } catch(e) {
        console.error("連線失敗 (請確認 python app.py 是否執行):", e);
    }

    renderDashboard();
    navigationStack = ['step-home', 'step-dashboard'];
    _showStep('step-dashboard');
}

function startNewBlock() {
    isInstantMode = false; 
    document.querySelectorAll('.tag-btn').forEach(btn => {
        btn.classList.remove('bg-blue-100', 'text-blue-600', 'border-blue-200');
        btn.classList.add('bg-gray-100', 'text-gray-600');
    });
    const txtArea = document.querySelector('textarea');
    if(txtArea) txtArea.value = '';
    const nameInput = document.getElementById('tripNameInput');
    if(nameInput) nameInput.value = '';
    const locInput = document.getElementById('locationInput');
    if(locInput) locInput.value = '';
    
    const startTimeEl = document.getElementById('blockStartTime');
    const endTimeEl = document.getElementById('blockEndTime');
    if(startTimeEl) startTimeEl.value = "10:00";
    if(endTimeEl) endTimeEl.value = "12:00";
    
    goToStep(2);
}

// --- [核心] Step 2: 生成 AI Prompt ---
function generateAiPayload() {
    let prevLat, prevLng;

    if (itineraryItems.length === 0) {
        prevLat = tripSettings.lat;
        prevLng = tripSettings.lng;
    } else {
        const lastItem = itineraryItems[itineraryItems.length - 1];
        prevLat = lastItem.lat; 
        prevLng = lastItem.lng;
    }
    
    const startTime = document.getElementById('blockStartTime').value;
    const endTime = document.getElementById('blockEndTime').value;

    const selectedTypes = [];
    document.querySelectorAll('.tag-btn').forEach(btn => {
        if (btn.classList.contains('bg-blue-100')) {
            selectedTypes.push(btn.innerText);
        }
    });

    if (selectedTypes.length === 0) {
        selectedTypes.push("隨機");
        console.log("使用者未選擇標籤，系統自動預設為：隨機");
    }

    const distanceInput = document.querySelector('input[type="range"]');
    const radius = distanceInput ? distanceInput.value + " km" : "0.5 km";

    const requirementInput = document.querySelector('textarea');
    const extraReq = requirementInput ? requirementInput.value : "";

    return {
        "time_slot": `${startTime} - ${endTime}`,
        "category_selection": selectedTypes,
        "max_travel_distance": radius,
        "prompt": extraReq,
        "companion": tripSettings.companion,
        "coordinates": {
            "lat": prevLat,
            "lng": prevLng
        }
    };
}

async function startLoading() {
    if(isInstantMode) {
        try {
            console.log("get position");
            const position = await getCurrentLocation();
            tripSettings.lat = position.lat;
            tripSettings.lng = position.lng;

            console.log("📍 已獲取當前位置:", tripSettings.lat, tripSettings.lng);
        }

        catch(error) {
            console.log("Fail to get current location");
        }
    }

    const loading = document.getElementById('loading-screen');
    const loadingText = document.getElementById('loading-text');
    
    loading.classList.remove('hidden'); loading.classList.add('flex');
    if(loadingText) loadingText.innerText = "正在儲存需求...";

    const payload = generateAiPayload();
    
    // 1. 傳送 request.json
    try {
        await fetch('/api/generate_ai_prompt', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
    } catch (e) { console.error("需求傳送失敗", e); }

    // 2. 等待並讀取 options.json
    if(loadingText) loadingText.innerText = "等待 AI 分析資料...";
    
    setTimeout(async () => {
        try {
            const response = await fetch('/api/get_ai_options');
            
            if (response.ok) {
                const data = await response.json();
                console.log("✅ 原始 AI 資料:", data.options);
                
                if (Array.isArray(data.options)) {
                    aiGeneratedOptions = data.options.map((item, index) => ({
                        id: Date.now() + index, 
                        
                        // 2. 欄位對應轉換
                        name: item.place_name,       // place_name -> name
                        type: item.category,         // category -> type
                        rating: item.rating,         // rating (不變)
                        tags: item.tags,             // tags (不變)
                        reason: item.ai_reason,      // ai_reason -> reason
                        distance: item.distance_info,// distance_info -> distance
                        lat: item.lat,               // lat (不變)
                        lng: item.lng,               // lng (不變)
                        timeRange: item.time_range   // 保留備用
                    }));
                }
                
                if(loadingText) loadingText.innerText = "生成完畢！";
                
                setTimeout(() => {
                    loading.classList.add('hidden'); loading.classList.remove('flex');
                    goToStep(3); // 這裡會觸發 renderOptions
                }, 500);

            } else {
                console.warn("尚未取得 options.json，使用 Mock 資料");
                loading.classList.add('hidden'); loading.classList.remove('flex');
                goToStep(3);
            }
        } catch (e) {
            console.error("讀取選項失敗:", e);
            loading.classList.add('hidden'); loading.classList.remove('flex');
            goToStep(3);
        }
    }, 2000);  // waiting time 
}

//Reload prompt
async function ReLoading() {
    const loading = document.getElementById('loading-screen');
    const loadingText = document.getElementById('loading-text');
    const inputElement = document.getElementById('new_prompt'); 

    loading.classList.remove('hidden'); loading.classList.add('flex');
    if(loadingText) loadingText.innerText = "正在儲存需求...";

    const payload = generateAiPayload();
    const new_prompt = inputElement.value;
    if (new_prompt.length > 0) {
        payload.prompt = new_prompt;
    }
    else {
        payload.prompt = "";
    }
    // 1. 傳送 request.json
    try {
        await fetch('/api/regenerate_ai_prompt', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
    } catch (e) { console.error("需求傳送失敗", e); }

    // 2. 等待並讀取 place.json
    if(loadingText) loadingText.innerText = "等待 AI 分析資料...";
    
    setTimeout(async () => {
        try {
            const response = await fetch('/api/get_ai_options');
            
            if (response.ok) {
                const data = await response.json();
                console.log("✅ 原始 AI 資料:", data.options);
                
                if (Array.isArray(data.options)) {
                    aiGeneratedOptions = data.options.map((item, index) => ({
                        // 1. 自動產生 ID (因為 json 裡沒有)
                        id: Date.now() + index, 
                        
                        // 2. 欄位對應轉換
                        name: item.place_name,       // place_name -> name
                        type: item.category,         // category -> type
                        rating: item.rating,         // rating (不變)
                        tags: item.tags,             // tags (不變)
                        reason: item.ai_reason,      // ai_reason -> reason
                        distance: item.distance_info,// distance_info -> distance
                        lat: item.lat,               // lat (不變)
                        lng: item.lng,               // lng (不變)
                        timeRange: item.time_range   // 保留備用
                    }));
                }
                
                if(loadingText) loadingText.innerText = "生成完畢！";
                
                setTimeout(() => {
                    loading.classList.add('hidden'); loading.classList.remove('flex');
                    goToStep(3); // 這裡會觸發 renderOptions
                }, 500);

            } else {
                console.warn("尚未取得 option.json，使用 Mock 資料");
                loading.classList.add('hidden'); loading.classList.remove('flex');
                goToStep(3);
            }
        } catch (e) {
            console.error("讀取選項失敗:", e);
            loading.classList.add('hidden'); loading.classList.remove('flex');
            goToStep(3);
        }
    }, 2000); 
}

// --- Step 3: 顯示選項 ---
function renderOptions() {
    const container = document.getElementById('options-container');
    if(!container) return;
    container.innerHTML = ''; 

    let displayData = (aiGeneratedOptions.length > 0) ? aiGeneratedOptions : mockOptions;
    if (aiGeneratedOptions.length > 0) {
        console.warn("ai");
    }
    else {
        console.warn("mock");
    }

    if (displayData.length === 0) {
        container.innerHTML = '<p class="text-center text-gray-400 py-10">目前沒有推薦選項</p>';
        return;
    }

    displayData.forEach(opt => {
        const card = document.createElement('div');
        card.className = "bg-white border border-gray-100 rounded-2xl p-4 card-shadow transition transform hover:scale-[1.01] cursor-pointer hover:border-blue-300";
        card.onclick = function() { selectAndProceed(opt); };
        
        //const bgImage = `https://source.unsplash.com/random/200x200/?${opt.type === '美食' ? 'food' : 'building'}&sig=${opt.id}`;
        card.innerHTML = `
            <div class="flex gap-4">
                <div class="w-20 h-20 bg-gray-200 rounded-lg flex-shrink-0 bg-cover bg-center" style="background-image: url('/static/images/icon2.png')"></div>
                <div class="flex-1">
                    <div class="flex justify-between items-start">
                        <h3 class="font-bold text-gray-800 text-lg">${opt.name}</h3>
                        <span class="bg-yellow-100 text-yellow-700 text-xs font-bold px-2 py-1 rounded flex items-center">
                            <i class="fa-solid fa-star mr-1"></i> ${opt.rating}
                        </span>
                    </div>
                    <div class="flex gap-2 mt-1 mb-2">
                        ${opt.tags.map(tag => `<span class="text-xs bg-gray-100 text-gray-500 px-2 py-0.5 rounded">${tag}</span>`).join('')}
                    </div>
                    <div class="text-xs text-gray-400 mb-2"><i class="fa-solid fa-location-dot"></i> 距離 ${opt.distance}</div>
                </div>
            </div>
            <div class="mt-3 bg-blue-50 p-3 rounded-lg relative">
                <p class="text-sm text-gray-700 leading-relaxed"><span class="font-bold text-blue-600">AI 推薦：</span>${opt.reason}</p>
            </div>
        `;
        container.appendChild(card);
    });
}

function selectAndProceed(option) {
    currentPendingItem = option; 
    
    const previewContainer = document.getElementById('final-selection');
    
    let bgImage;
    if (option.lat && option.lng) {
        bgImage = `/api/map_image?lat=${option.lat}&lng=${option.lng}`;
    } else {
        bgImage = getImageUrl(option.type, option.id); 
    }
    
    const startTimeEl = document.getElementById('blockStartTime');
    const endTimeEl = document.getElementById('blockEndTime');
    const startTime = startTimeEl ? startTimeEl.value : "10:00";
    const endTime = endTimeEl ? endTimeEl.value : "12:00";

    document.getElementById('preview-time').innerText = isInstantMode ? "即時出發" : `${startTime} - ${endTime}`;
    document.getElementById('preview-reason').innerText = option.reason;

    previewContainer.innerHTML = `
        <h2 class="text-2xl font-bold text-gray-800 mb-2">${option.name}</h2>
        
        <div class="h-64 relative w-full rounded-xl overflow-hidden shadow-sm mb-4 bg-gray-100">
            <img src="${bgImage}" class="w-full h-full object-cover" alt="地圖預覽">
            
            <div class="absolute bottom-2 right-2 bg-white/90 backdrop-blur px-2 py-1 rounded text-[10px] font-bold text-gray-600 shadow-sm">
                <i class="fa-solid fa-map-location-dot"></i> 地點位置
            </div>
        </div>

        <div class="flex gap-2 mb-2">
            ${option.tags.map(t => `<span class="bg-gray-100 text-gray-600 px-3 py-1 rounded-full text-xs font-bold">${t}</span>`).join('')}
        </div>
        <div class="text-sm text-gray-500">
            <i class="fa-solid fa-star text-yellow-400 mr-1"></i> ${option.rating} 評分
        </div>
    `;

    goToStep(4);
}

function renderStep4Buttons() {
    const container = document.getElementById('step-4-actions');
    if(!container) return;
    container.innerHTML = ''; 

    if (isInstantMode) {
        const isFav = currentPendingItem && savedFavorites.some(f => f.id === currentPendingItem.id);
        const btnClass = isFav 
            ? "flex-1 bg-pink-500 text-white font-bold py-3 rounded-xl border border-pink-600 hover:bg-pink-600 transition flex justify-center items-center gap-2"
            : "flex-1 bg-pink-50 text-pink-600 font-bold py-3 rounded-xl border border-pink-100 hover:bg-pink-100 transition flex justify-center items-center gap-2";
        const btnIcon = isFav ? '<i class="fa-solid fa-heart"></i>' : '<i class="fa-regular fa-heart"></i>';
        const btnText = isFav ? "已收藏" : "加入最愛";

        container.innerHTML = `
            <button onclick="startInstantNavigation()" class="w-full bg-green-600 text-white font-bold py-4 rounded-xl shadow-lg shadow-green-200 hover:bg-green-700 transition flex justify-center items-center gap-2">
                <i class="fa-solid fa-location-arrow"></i> 立即導航前往
            </button>
            <div class="flex gap-3">
                <button onclick="toggleFavoriteFromStep4()" class="${btnClass}">
                    ${btnIcon} ${btnText}
                </button>
                <button onclick="goBack()" class="flex-1 bg-gray-100 text-gray-600 font-bold py-3 rounded-xl hover:bg-gray-200 transition">
                    重新選擇
                </button>
            </div>
        `;
    } else {
        container.innerHTML = `
            <button onclick="confirmAndAddToDashboard()" class="w-full bg-blue-600 text-white font-bold py-4 rounded-xl shadow-lg shadow-blue-200 hover:bg-blue-700 transition flex justify-center items-center gap-2">
                <i class="fa-solid fa-check"></i> 確認加入行程
            </button>
            <button onclick="goBack()" class="w-full mt-3 text-gray-400 text-sm py-2 hover:text-gray-600">
                重新選擇
            </button>
        `;
    }
}

// --- [核心] Step 4: 確認並傳送單一項目 (含座標) ---
async function confirmAndAddToDashboard() {
    if (currentPendingItem) {
        const startTimeEl = document.getElementById('blockStartTime');
        const endTimeEl = document.getElementById('blockEndTime');
        const startTime = startTimeEl ? startTimeEl.value : "10:00";
        const endTime = endTimeEl ? endTimeEl.value : "12:00";

        const newItem = {
            ...currentPendingItem, 
            timeRange: `${startTime} - ${endTime}`,
            uuid: Date.now()
        };
        itineraryItems.push(newItem);
        itineraryItems.sort((a, b) => a.timeRange.localeCompare(b.timeRange));
        renderDashboard();

        if (activeServerTripId) {
            try {
                const itemPayload = {
                    trip_id: activeServerTripId,
                    item: {
                        place_name: newItem.name,
                        category: newItem.type,
                        time_range: newItem.timeRange,
                        rating: newItem.rating,
                        tags: newItem.tags,
                        ai_reason: newItem.reason,
                        distance_info: newItem.distance,
                        lat: newItem.lat, 
                        lng: newItem.lng
                    }
                };
                
                fetch('/api/add_item', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(itemPayload)
                }).then(res => res.json()).then(data => console.log("後端同步:", data.message));

            } catch (e) {
                console.error("後端同步失敗:", e);
            }
        }

        navigationStack = ['step-home', 'step-dashboard'];
        _showStep('step-dashboard');
    }
}

// --- Favorites Logic ---
function toggleFavoriteFromStep4() {
    if(!currentPendingItem) return;
    const index = savedFavorites.findIndex(f => f.id === currentPendingItem.id);
    if (index > -1) {
        savedFavorites.splice(index, 1);
    } else {
        savedFavorites.push(currentPendingItem);
    }
    renderStep4Buttons();
}

function toggleFavoriteFromList(itemId) {
    const index = savedFavorites.findIndex(f => f.id === itemId);
    if (index > -1) {
        savedFavorites.splice(index, 1);
    }
    renderFavorites();
}

function renderFavorites() {
    const container = document.getElementById('favorites-list-container');
    container.innerHTML = '';
    
    if(savedFavorites.length === 0) {
        container.innerHTML = `<div class="bg-gray-50 border border-gray-100 rounded-2xl p-6 text-center text-gray-400 text-sm">尚未有收藏的項目</div>`;
        return;
    }

    savedFavorites.forEach(item => {
        //const bgImage = `https://source.unsplash.com/random/200x200/?${item.type === '美食' ? 'food' : 'building'}&sig=${item.id}`;
        container.innerHTML += `
             <div class="bg-white border border-gray-100 rounded-xl p-3 flex gap-3 shadow-sm mb-4 relative">
                <div class="w-16 h-16 bg-gray-200 rounded-lg flex-shrink-0 bg-cover bg-center" style="background-image: url('/static/images/icon2.png')"></div>
                <div class="flex-1 min-w-0">
                    <h4 class="font-bold text-gray-800 truncate">${item.name}</h4>
                    <p class="text-xs text-gray-500 truncate mt-1">${item.type} • ${item.tags[0] || '熱門'}</p>
                    <div class="text-xs text-gray-400 mt-1"><i class="fa-solid fa-location-dot"></i> ${item.distance}</div>
                </div>
                <button onclick="toggleFavoriteFromList(${item.id})" class="absolute top-3 right-3 text-pink-500 hover:text-pink-600 bg-pink-50 w-8 h-8 rounded-full flex items-center justify-center transition hover:bg-pink-100">
                    <i class="fa-solid fa-heart"></i>
                </button>
            </div>
        `;
    });
}

function startInstantNavigation() {
    if(!currentPendingItem) return;
    const query = currentPendingItem.name;
    const mapUrl = `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(query)}`;
    window.open(mapUrl, '_blank');
}

// --- [核心] 完成儲存 & 跳轉詳情 ---
function saveCurrentTrip() {
    if(itineraryItems.length === 0) {
        alert("您的行程表是空的，請先新增至少一個行程喔！");
        return;
    }

    const tripId = activeServerTripId || Date.now().toString(); 

    // 將前端資料結構轉為後端結構，以便 openTripDetail 讀取
    const finalTripData = {
        id: tripId,
        meta: {
            trip_name: tripSettings.tripName,
            location: tripSettings.location,
            date: tripSettings.date,
            companion: tripSettings.companion,
            transport: tripSettings.transport,
            lat: tripSettings.lat,
            lng: tripSettings.lng
        },
        schedule: itineraryItems.map(item => ({
            place_name: item.name,
            category: item.type,
            time_range: item.timeRange, 
            rating: item.rating,
            tags: item.tags,
            ai_reason: item.reason,
            distance_info: item.distance,
            lat: item.lat,
            lng: item.lng
        }))
    };

    savedTrips.unshift(finalTripData); 
    activeServerTripId = null; 
    
    openTripDetail(tripId);
    navigationStack = ['step-home', 'step-dashboard', 'step-trip-detail'];
}

function openTripDetail(tripId) {
    // 依據 ID 查找 (字串)
    const trip = savedTrips.find(t => t.id === tripId);
    if(!trip) return;

    currentViewingTripId = tripId;
    const nameInput = document.getElementById('detail-trip-name');
    if(nameInput) nameInput.value = trip.meta.trip_name;

    const badgeContainer = document.getElementById('detail-badges');
    badgeContainer.innerHTML = `
        <span class="bg-blue-100 text-blue-600 text-xs font-bold px-2 py-1 rounded-md"><i class="fa-regular fa-calendar mr-1"></i>${trip.meta.date}</span>
        <span class="bg-purple-100 text-purple-600 text-xs font-bold px-2 py-1 rounded-md"><i class="fa-solid fa-user-group mr-1"></i>${trip.meta.companion}</span>
        <span class="bg-green-100 text-green-600 text-xs font-bold px-2 py-1 rounded-md"><i class="fa-solid fa-car-side mr-1"></i>${trip.meta.transport}</span>
    `;

    const listContainer = document.getElementById('detail-list-container');
    listContainer.innerHTML = '';
    
    listContainer.innerHTML += `
        <div class="relative pl-8">
            <div class="absolute -left-[9px] top-1 w-4 h-4 bg-gray-400 rounded-full border-2 border-white shadow"></div>
            <h4 class="font-bold text-gray-800">出發：${trip.meta.location}</h4>
        </div>
    `;

    trip.schedule.forEach(item => {
        //const bgImage = `https://source.unsplash.com/random/200x200/?${item.category === '美食' ? 'food' : 'building'}&sig=${Math.random()}`;
        listContainer.innerHTML += `
            <div class="relative pl-8">
                <div class="absolute -left-[9px] top-6 w-4 h-4 bg-blue-600 rounded-full border-2 border-white shadow ring-2 ring-blue-100"></div>
                <div class="bg-white border border-gray-100 rounded-xl p-3 flex gap-3 shadow-sm">
                    <div class="w-14 h-14 bg-gray-200 rounded-lg flex-shrink-0 bg-cover bg-center" style="background-image: url('/static/images/icon.png')"></div>
                    <div class="flex-1 min-w-0">
                        <div class="flex justify-between items-center mb-1">
                            <h4 class="font-bold text-gray-800 truncate">${item.place_name}</h4>
                            <span class="text-xs font-bold text-blue-600 bg-blue-50 px-2 py-0.5 rounded">${item.time_range}</span>
                        </div>
                        <p class="text-xs text-gray-500 truncate">${item.category} • ${item.ai_reason}</p>
                    </div>
                </div>
            </div>
            <div class="pl-8 py-1">
            </div>
        `;
    });

    goToStep('trip-detail');
}

function startNavigation() {
    if (!currentViewingTripId) return;
    const trip = savedTrips.find(t => t.id === currentViewingTripId);
    if (!trip) return;

    let query = trip.meta.location;
    if (trip.schedule && trip.schedule.length > 0) {
        query = trip.schedule[0].place_name;
    }
    const mapUrl = `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(query)}`;
    window.open(mapUrl, '_blank');
}

function renderDashboard() {
    const listContainer = document.getElementById('itinerary-list');
    document.getElementById('dashboard-title-display').innerText = tripSettings.tripName;
    document.getElementById('dashboard-info-display').innerText = `${tripSettings.date} • ${tripSettings.location} • ${tripSettings.transport}`;
    
    listContainer.innerHTML = '';
    listContainer.innerHTML += `
        <div class="relative pl-8">
            <div class="absolute -left-[9px] top-1 w-4 h-4 bg-gray-400 rounded-full border-2 border-white shadow"></div>
            <h4 class="font-bold text-gray-800">出發：${tripSettings.location}</h4>
            <p class="text-xs text-gray-500">旅程開始 (${tripSettings.companion}行)</p>
        </div>
    `;

    itineraryItems.forEach(item => {
        //const bgImage = `https://source.unsplash.com/random/200x200/?${item.type === '美食' ? 'food' : 'building'}&sig=${item.id}`;
        listContainer.innerHTML += `
            <div class="relative pl-8 group">
                <div class="absolute -left-[9px] top-6 w-4 h-4 bg-blue-600 rounded-full border-2 border-white shadow ring-2 ring-blue-100 group-hover:ring-blue-300 transition"></div>
                <div class="bg-white border border-gray-100 rounded-xl p-3 flex gap-3 shadow-sm hover:shadow-md transition">
                    <div class="w-14 h-14 bg-gray-200 rounded-lg flex-shrink-0 bg-cover bg-center" style="background-image: url('/static/images/icon2.png')"></div>
                    <div class="flex-1 min-w-0">
                        <div class="flex justify-between items-center mb-1">
                            <h4 class="font-bold text-gray-800 truncate">${item.name}</h4>
                            <span class="text-xs font-bold text-blue-600 bg-blue-50 px-2 py-0.5 rounded">${item.timeRange}</span>
                        </div>
                        <p class="text-xs text-gray-500 truncate">${item.type} • ${item.reason}</p>
                    </div>
                    <button class="text-gray-300 hover:text-red-500 px-1"><i class="fa-solid fa-trash-can"></i></button>
                </div>
            </div>
             <div class="pl-8 py-1">
            </div>
        `;
    });

    if(itineraryItems.length === 0) {
        listContainer.innerHTML += `<div class="pl-8 py-4 text-gray-400 text-sm italic">目前還沒有行程...</div>`;
    }
}

// --- History & Tabs ---

async function fetchAndRenderHistory() {
    try {
        const response = await fetch('/api/get_all_trips');
        const data = await response.json();
        
        if (data.status === 'success') {
            savedTrips = data.trips; 
            renderHistory(); 
        } else {
            console.error("無法讀取行程:", data.message);
        }
    } catch (e) {
        console.error("連線失敗:", e);
    }
}

function renderHistory() {
    const container = document.getElementById('history-list-container');
    container.innerHTML = '';
    if(savedTrips.length === 0) {
        container.innerHTML = `<div class="bg-gray-50 border border-gray-100 rounded-2xl p-6 text-center text-gray-400 text-sm">尚未有儲存的行程</div>`;
        return;
    }
    savedTrips.forEach(trip => {
        const tripIdParam = `'${trip.id}'`;
        const lat = trip.meta.lat ? trip.meta.lat.toFixed(4) : "未取得";
        const lng = trip.meta.lng ? trip.meta.lng.toFixed(4) : "未取得";
        const locationDisplay = (lat !== "未取得") ? `<span class="text-[10px] bg-gray-100 px-1 rounded text-gray-500 ml-2"><i class="fa-solid fa-map-pin"></i> ${lat}, ${lng}</span>` : ``;

        container.innerHTML += `
            <div onclick="openTripDetail(${tripIdParam})" class="bg-white rounded-2xl p-4 card-shadow flex gap-4 mb-4 border-l-4 border-blue-600 cursor-pointer hover:shadow-lg transition">
                <div class="flex-1">
                    <div class="flex justify-between items-start mb-1">
                        <h4 class="font-bold text-lg text-gray-800">${trip.meta.trip_name}</h4>
                        <span class="bg-blue-100 text-blue-600 text-xs font-bold px-2 py-1 rounded">已儲存</span>
                    </div>
                    <p class="text-sm text-gray-500 mb-2 flex items-center">
                        <i class="fa-regular fa-calendar mr-2"></i>${trip.meta.date} • ${trip.meta.location}
                        ${locationDisplay}
                    </p>
                    <div class="text-xs text-gray-400 mb-3 pl-2 border-l-2 border-gray-100">
                        ${trip.schedule.length > 0 ? `<div>• ${trip.schedule[0].place_name}</div>` : ''}
                        ${trip.schedule.length > 1 ? `<div>• ${trip.schedule[1].place_name}</div>` : ''}
                        ${trip.schedule.length > 2 ? `<div>...還有 ${trip.schedule.length - 2} 個行程</div>` : ''}
                    </div>
                </div>
            </div>
        `;
    });
}

function switchTab(tabName) {
    updateBottomNavState(tabName);
    
    activeServerTripId = null;
    if (tabName === 'home') {
         navigationStack = ['step-home'];
         _showStep('step-home');
         return;
    }

    const historySection = document.getElementById('tab-history');
    const favoritesSection = document.getElementById('tab-favorites');
    document.querySelectorAll('.step-section').forEach(el => el.classList.remove('active'));

    if (tabName === 'history') {
        historySection.classList.add('active');
        fetchAndRenderHistory(); 
    } else if (tabName === 'favorites') {
        favoritesSection.classList.add('active');
        renderFavorites();
    }
    window.scrollTo(0,0);
}

function updateBottomNavState(activeTabName) {
    const navBtns = document.querySelectorAll('.nav-btn');
    navBtns.forEach(btn => {
        btn.classList.remove('text-blue-600', 'active');
        btn.classList.add('text-gray-400');
    });

    let targetIndex = 0;
    if (activeTabName === 'history') targetIndex = 1;
    if (activeTabName === 'favorites') targetIndex = 2; 

    if(navBtns[targetIndex]) {
        navBtns[targetIndex].classList.remove('text-gray-400');
        navBtns[targetIndex].classList.add('text-blue-600', 'active');
    }
}