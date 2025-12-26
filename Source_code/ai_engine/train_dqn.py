import torch
import torch.optim as optim
import torch.nn as nn
import numpy as np
import random

from db import load_posts, load_all_utilities  # TODO: nếu có hàm load_favorites thì import thêm
from dqn_model import DQN
from utils import RoomEnv

# ======================================================
# 1. LOAD DATA TỪ DATABASE
# ======================================================
df = load_posts()
posts = df.to_dict(orient="records")

# utilities: {phong_id: [id_dich_vu1, id_dich_vu2, ...]}
utilities = load_all_utilities()

# favorites: tạm thời để trống (nếu m đã có bảng yeu_thich
# thì có thể tự build list phong_id vào đây)
favorites = []  # ví dụ: [1, 5, 9]

# Chuẩn hóa rooms cho RoomEnv
rooms = []
for p in posts:
    # bắt buộc phải có các field này trong load_posts():
    #   id, gia_thue (hoặc gia), dien_tich, days_empty
    room = {
        "id": p["id"],
        "gia_thue": float(p.get("gia_thue", p.get("gia", 0))),  # fallback nếu cột tên 'gia'
        "dien_tich": float(p.get("dien_tich", 0)),
        # nếu db chưa có days_empty thì m tính ở db.py dựa trên phong + hop_dong
        "days_empty": float(p.get("days_empty", 0)),
    }
    rooms.append(room)

env = RoomEnv(rooms, utilities, favorites)

# ======================================================
# 2. CẤU HÌNH USER "GIẢ" KHI TRAIN
#    (lúc deploy thực tế sẽ lấy từ UI)
# ======================================================
user = {
    "max_price": 3_000_000,   # ngân sách (VNĐ)
    "area": 20,               # diện tích mong muốn (m2)
    "utilities": [1, 2, 3],   # id dịch vụ mong muốn (ví dụ)
}

# Lấy state ban đầu và flatten thành vector 1D
state = env.reset(user)
state = state.reshape(-1)
state_size = state.shape[0]
action_size = env.num_actions

print("STATE SIZE:", state_size)
print("ACTIONS (số phòng):", action_size)

# ======================================================
# 3. KHỞI TẠO MÔ HÌNH DQN
# ======================================================
policy_net = DQN(state_size, action_size)
target_net = DQN(state_size, action_size)
target_net.load_state_dict(policy_net.state_dict())
target_net.eval()

optimizer = optim.Adam(policy_net.parameters(), lr=0.001)

memory = []
BATCH = 32
GAMMA = 0.99
MAX_MEMORY = 5000

# Epsilon-greedy cho exploration
EPS_START = 1.0
EPS_END = 0.05
EPS_DECAY = 300
steps_done = 0


# ======================================================
# 4. HÀM CHỌN ACTION (PHÒNG)
# ======================================================
def select_action(state_vec):
    global steps_done

    eps_threshold = EPS_END + (EPS_START - EPS_END) * \
        np.exp(-1.0 * steps_done / EPS_DECAY)
    steps_done += 1

    if random.random() < eps_threshold:
        # random 1 phòng
        return random.randrange(action_size)
    else:
        with torch.no_grad():
            s = torch.tensor(state_vec, dtype=torch.float32).unsqueeze(0)
            q_values = policy_net(s)
            return int(torch.argmax(q_values).item())


# ======================================================
# 5. HÀM TRAIN 1 BATCH TỪ REPLAY MEMORY
# ======================================================
def train_step():
    if len(memory) < BATCH:
        return

    batch = random.sample(memory, BATCH)
    states, actions, rewards, next_states = zip(*batch)

    states = torch.tensor(states, dtype=torch.float32)
    next_states = torch.tensor(next_states, dtype=torch.float32)
    rewards = torch.tensor(rewards, dtype=torch.float32)
    actions = torch.tensor(actions, dtype=torch.long)

    # Q(s, a)
    q_values = policy_net(states)
    q_value = q_values.gather(1, actions.unsqueeze(1)).squeeze(1)

    # max_a' Q_target(s', a')
    next_q = target_net(next_states).max(1)[0].detach()
    expected = rewards + GAMMA * next_q

    loss = nn.MSELoss()(q_value, expected)

    optimizer.zero_grad()
    loss.backward()
    optimizer.step()


# ======================================================
# 6. VÒNG LẶP TRAIN
# ======================================================
EPISODES = 400

for ep in range(EPISODES):
    # reset môi trường với cùng 1 user giả
    state = env.reset(user)
    state = state.reshape(-1)

    # chọn action theo chính sách epsilon-greedy
    action = select_action(state)

    # môi trường trả về reward cho action đó
    next_state, reward, done, _ = env.step(action)
    next_state = next_state.reshape(-1)

    # lưu vào replay memory
    if len(memory) >= MAX_MEMORY:
        memory.pop(0)
    memory.append((state, action, reward, next_state))

    # train 1 step
    train_step()

    # update target_net định kỳ
    if ep % 40 == 0:
        target_net.load_state_dict(policy_net.state_dict())
        print(f"Episode: {ep}, reward: {reward:.3f}")

# ======================================================
# 7. LƯU MODEL
# ======================================================
torch.save(policy_net.state_dict(), "dqn_room.pt")
print("🔥 Train xong model dqn_room.pt với state_size =", state_size)
