from fastapi import FastAPI
import torch
import numpy as np

from db import load_posts, load_all_utilities, load_favorites  # nhớ thêm hàm này
from utils import RoomEnv
from dqn_model import DQN

app = FastAPI()

# ==============================================
# 1. LOAD DỮ LIỆU PHÒNG
# ==============================================
posts_df = load_posts()
posts_raw = posts_df.to_dict(orient="records")

# Load tiện ích phòng: {phong_id: [id_tienich1, id2]}
utilities = load_all_utilities()

# Chuẩn hoá dữ liệu → build thành rooms chuẩn cho RL
rooms = []
for p in posts_raw:
    rooms.append({
        "id": p["phong_id"],
        "gia_thue": float(p.get("gia") or 0),
        "dien_tich": float(p.get("dien_tich") or 0),
        "days_empty": float(p.get("days_empty") or 0),
    })

# favorites load sau trong API → tuỳ user
dummy_fav = []

# Khởi tạo ENV
env = RoomEnv(rooms, utilities, dummy_fav)


# ==============================================
# 2. LOAD MODEL
# ==============================================
# Build state mẫu để lấy state_size
sample_user = {"max_price": 1, "area": 1, "utilities": []}
sample_state = env.reset(sample_user)

state_size = sample_state.reshape(-1).shape[0]
action_size = len(rooms)

# Load DQN
model = DQN(state_size, action_size)
model.load_state_dict(torch.load("dqn_room.pt", map_location="cpu"))
model.eval()


# ==============================================
# 3. API GỢI Ý TOP 3 PHÒNG
# ==============================================
@app.post("/recommend_top3")
def recommend_top3(data: dict):

    # ========================
    # INPUT TỪ UI
    # ========================
    user_id = data.get("user_id")
    max_price = float(data.get("max_price", 0))
    area = float(data.get("area", 0))
    user_utils = data.get("utilities", [])  # list id dịch vụ

    # ========================
    # LOAD FAVORITES TỪ DB
    # ========================
    try:
        favorites = load_favorites(user_id)
    except:
        favorites = []

    # Cập nhật favorite cho env
    env.favorites = favorites

    # Build user for RL
    user = {
        "max_price": max_price,
        "area": area,
        "utilities": user_utils,
    }

    # Build RL state
    state = env.reset(user).reshape(1, -1)

    # ==========================
    # RUN DQN → LẤY Q-VALUE
    # ==========================
    with torch.no_grad():
        q_values = model(torch.tensor(state, dtype=torch.float32))[0].numpy()

    # ==========================
    # SẮP XẾP PHÒNG THEO Q
    # ==========================
    sorted_idx = np.argsort(q_values)[::-1]  # giảm dần

    top3_rooms = []
    for idx in sorted_idx[:3]:
        room_id = rooms[idx]["id"]

        # Map lại về bài đăng gốc
        p = next((x for x in posts_raw if x["phong_id"] == room_id), None)
        if p:
            top3_rooms.append({
                "bai_dang_id": p.get("bai_dang_id"),
                "tieu_de": p.get("tieu_de"),
                "gia": float(p.get("gia") or 0),
                "dien_tich": float(p.get("dien_tich") or 0),
                "tang": p.get("tang"),
                "ten_day_tro": p.get("ten_day_tro"),
                "phong_id": p.get("phong_id"),
                "dia_chi": p.get("dia_chi_daytro"),
                "tien_ich": utilities.get(p["phong_id"], []),
                "mo_ta": p.get("mo_ta"),
                "q_value": float(q_values[idx]),
                "is_favorite": 1 if p["phong_id"] in favorites else 0
            })

    return {"recommend": top3_rooms}
