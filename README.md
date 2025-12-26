# 🏆 Đồ Án Tốt Nghiệp: Hệ Thống Quản Lý Nhà Trọ Thông Minh

<p align="center">
  <img src="https://img.shields.io/badge/Laravel-FF2D20?style=for-the-badge&logo=laravel&logoColor=white" />
  <img src="https://img.shields.io/badge/Flutter-02569B?style=for-the-badge&logo=flutter&logoColor=white" />
  <img src="https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white" />
  <img src="https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=FastAPI&logoColor=white" />
</p>

---

## 📊 Tổng Quan Hệ Thống
Dự án là một hệ sinh thái toàn diện hỗ trợ quản lý nhà trọ, kết hợp giữa nền tảng Web (Laravel), ứng dụng di động (Flutter) và trí tuệ nhân tạo (Python) để tối ưu hóa việc vận hành.

### 📂 Cấu trúc thư mục
| Thành phần | Công nghệ | Chức năng | Cổng (Port) |
| :--- | :--- | :--- | :--- |
| **nhatro-main** | Laravel | Hệ thống quản lý & API chính | `8001` |
| **NhaTro1** | Laravel | Giao diện quản lý phụ | `8000` |
| **ai_engine** | Python | Xử lý thuật toán thông minh | `8002` |
| **DATN_Mobile** | Flutter | Ứng dụng di động cho người dùng | Mobile |

---

## 🚀 Hướng Dẫn Khởi Chạy

### 🧠 1. AI Engine (Python)
Mở terminal tại thư mục `ai_engine`:
```bash
cd ai_engine
# Cài đặt thư viện nếu cần: pip install -r requirements.txt
uvicorn api:app --reload --port 8002
