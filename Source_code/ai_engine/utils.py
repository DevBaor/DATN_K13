import numpy as np
from datetime import datetime


class RoomEnv:
    def __init__(self, rooms, utilities, favorites):
        """
        rooms: danh sách phòng trống [{id, gia_thue, dien_tich, days_empty}, ...]
        utilities: {phong_id: [id_dich_vu1, id_dich_vu2]}
        favorites: [phong_id1, phong_id2]
        """
        self.rooms = rooms
        self.utilities = utilities
        self.favorites = favorites
        self.num_actions = len(rooms)

    # ================================
    # RESET
    # ================================
    def reset(self, user):
        """
        user = {
            "max_price": int,
            "area": float,
            "utilities": [id1, id2]
        }
        """
        self.user = user
        return self.build_state()

    # ================================
    # NORMALIZATION HELPERS
    # ================================
    def norm_price(self, price):
        return price / 10_000_000

    def norm_area(self, area):
        return area / 50

    def norm_days(self, days):
        return min(days / 180, 1)

    # ================================
    # CORE STATE VECTOR
    # ================================
    def build_state(self):
        """
        Mỗi phòng → 1 vector 5 chiều
        """
        feature_list = []

        for room in self.rooms:
            price_norm = self.norm_price(room["gia_thue"])
            area_norm = self.norm_area(room["dien_tich"])

            # tiện ích khách muốn
            room_utils = self.utilities.get(room["id"], [])
            match = len(set(room_utils) & set(self.user["utilities"]))
            util_score = match / max(len(self.user["utilities"]), 1)

            # yêu thích
            is_fav = 1 if room["id"] in self.favorites else 0

            # days empty
            days_empty_norm = self.norm_days(room["days_empty"])

            feature_list.append([
                price_norm,
                area_norm,
                util_score,
                is_fav,
                days_empty_norm
            ])

        return np.array(feature_list, dtype=np.float32)

    # ================================
    # REWARD FUNCTION
    # ================================
    def step(self, action):
        room = self.rooms[action]
        reward = 0

        # 1. GIÁ
        reward += 2 if room["gia_thue"] <= self.user["max_price"] else -5

        # 2. DIỆN TÍCH
        if abs(room["dien_tich"] - self.user["area"]) <= 5:
            reward += 3
        else:
            reward -= 2

        # 3. TIỆN ÍCH
        room_utils = self.utilities.get(room["id"], [])
        match = len(set(room_utils) & set(self.user["utilities"]))
        util_score = match / max(len(self.user["utilities"]), 1)
        reward += util_score * 5

        # 4. YÊU THÍCH
        if room["id"] in self.favorites:
            reward += 5

        # 5. NGÀY TRỐNG
        reward += self.norm_days(room["days_empty"]) * 3

        next_state = self.build_state()
        done = True

        return next_state, float(reward), done, {}
