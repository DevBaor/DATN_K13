import torch
import torch.nn as nn
import torch.nn.functional as F


class DQN(nn.Module):
    def __init__(self, state_size, action_size):
        """
        state_size = num_rooms * 5
        action_size = num_rooms
        """
        super(DQN, self).__init__()

        # Network cho từng phòng (embedding 5 → 64)
        self.room_fc1 = nn.Linear(5, 64)
        self.room_fc2 = nn.Linear(64, 64)

        # Attention nhẹ để học trọng số từng phòng
        self.attn = nn.Linear(64, 1)

        # Layer cuối dự đoán Q-value cho từng phòng
        self.final_fc1 = nn.Linear(64, 128)
        self.final_fc2 = nn.Linear(128, 1)

        self.action_size = action_size

    def forward(self, x):
        """
        x shape: (batch, state_size)
        Reshape → (batch, num_rooms, 5)
        """
        batch = x.size(0)
        num_rooms = self.action_size

        x = x.view(batch, num_rooms, 5)  # chia lại từng phòng

        # Embedding từng phòng
        h = F.relu(self.room_fc1(x))
        h = F.relu(self.room_fc2(h))  # (batch, rooms, 64)

        # attention: tính độ quan trọng từng phòng
        attn_weights = torch.softmax(self.attn(h), dim=1)  # (batch, rooms, 1)

        # Weighted sum embedding
        h = h * attn_weights

        # Dự đoán Q-value cho từng phòng
        q_values = []
        for i in range(num_rooms):
            q = F.relu(self.final_fc1(h[:, i]))
            q = self.final_fc2(q)
            q_values.append(q)

        q_values = torch.cat(q_values, dim=1)  # (batch, num_rooms)

        return q_values
