# Project Log: TeamTalk 5 Bot Development Skill (`team_talk_bot_developman_skill`)

**Ngày thực hiện:** 17/10/2026  
**Mục tiêu:** Tạo và hoàn thiện một skill AI toàn diện bằng Tiếng Anh chuyên dụng cho việc phát triển bot TeamTalk 5 bằng Python (sử dụng thư viện `teamtalkpy` và `TeamTalk5.dll`), tích hợp sẵn bộ tài nguyên đóng gói, script tự động hóa chẩn đoán / thiết lập dự án, và hệ thống tài liệu API chi tiết từ A-Z.

---

## 1. Kết quả Đạt được (Deliverables Summary)

### 1.1 Kích hoạt & Ứng dụng Prompt Optimizer
- Đã đọc và vận dụng nguyên lý của skill `llm-prompt-optimizer` (khung RSCIT: Role, Situation, Constraints, Instructions, Template; mẫu chain-of-thought, hướng dẫn rõ ràng, không giả định ngữ cảnh, tối ưu token).
- Toàn bộ nội dung của skill, tài liệu API, hướng dẫn, script và templates đều được biên soạn bằng **Tiếng Anh** chuyên nghiệp, chuẩn mực.

### 1.2 Đóng gói Thư viện Runtime (`resources/teamtalkpy/`)
- Trích xuất từ TeamTalk 5 SDK (`tt5sdk_v5.23a_win64`):
  - `TeamTalk5.py` (Wrapper ctypes cho Python)
  - `__init__.py`
  - `TeamTalk5.dll` (Engine 64-bit client)
- **Cải tiến tính tương thích (Portability Patch):**
  - Khắc phục lỗi `FileNotFoundError` của `os.add_dll_directory` trên Windows khi chạy độc lập ngoài thư mục SDK.
  - Tự động phát hiện và thêm cả thư mục hiện tại (`os.getcwd()`), thư mục chứa `TeamTalk5.py`, và fallback sang nạp trực tiếp đường dẫn DLL. Giúp bot mới có thể mang theo thư mục `teamtalkpy` và chạy ở bất kỳ đâu mà không bị lỗi thiếu DLL.

### 1.3 Công cụ Tự động hóa (`scripts/setup_teamtalk_bot.py`)
Cung cấp CLI hỗ trợ AI và lập trình viên:
- `init`: Tự động khởi tạo cấu trúc dự án bot chuẩn (`bot.py`, `config.json`, `teamtalkpy/`, `TeamTalk5.dll`, `requirements.txt`, `.gitignore`, `README.md`).
- `check`: Chẩn đoán dự án bot hiện có:
  - Kiểm tra kiến trúc Python (yêu cầu 64-bit cho DLL 64-bit).
  - Kiểm tra sự hiện diện của `TeamTalk5.py` và `TeamTalk5.dll`.
  - Kiểm tra file cấu hình và entrypoint.
  - Kiểm tra nạp và gọi hàm `TeamTalk5.getVersion()`.
- `fix`: Tự động sao chép các file runtime còn thiếu từ kho tài nguyên đóng gói vào dự án.
- `download-sdk`: Tự động tải bản SDK v5.23a chính thức từ BearWare.dk khi cần nạp mới trên máy khác.
- `clean`: Trích xuất file thiết yếu (`TeamTalk5.dll` & `TeamTalk5.py`) và dọn dẹp hàng trăm MB file demo/C++/docs không cần thiết.

### 1.4 Hệ thống Tài liệu Tham khảo Chuyên sâu (`references/`)
1. [`teamtalkpy-api.md`](references/teamtalkpy-api.md):
   - Thống kê và tài liệu hóa chi tiết **93 Classes/Structs/Enums** (như `User`, `UserAccount`, `Channel`, `ServerProperties`, `TextMessage`, `AudioBlock`, v.v.).
   - Toàn bộ **118 Methods** của class `TeamTalk` (kết nối, xác thực, quản lý kênh, gửi nhận tin nhắn, truyền âm thanh, xử lý khối âm thanh thô, quản trị người dùng, quản trị server).
   - Danh mục **55 ClientEvent** và các hàm callback tương ứng trong `runEventLoop()`.
   - Quy tắc xử lý chuỗi UTF qua hàm `ttstr()` và giới hạn độ dài `TT_STRLEN = 512`.
2. [`project-structure.md`](references/project-structure.md):
   - Cấu trúc cây thư mục chuẩn cho bot TeamTalk.
   - Cơ chế nạp DLL của Python 3.8+ trên Windows (`os.add_dll_directory`).
   - Yêu cầu Bitness (64-bit Python bắt buộc với 64-bit DLL).
   - Hướng dẫn triển khai trên Linux/macOS headless.
3. [`audio-streaming.md`](references/audio-streaming.md):
   - Truyền phát file âm thanh (MP3, WAV) qua `startStreamingMediaFileToChannel` và `stopStreamingMediaFileToChannel`.
   - Cơ chế Push-to-Talk và kích hoạt giọng nói (`enableVoiceTransmission`, `enableVoiceActivation`).
   - Chèn và xử lý âm thanh thô PCM 16-bit qua `AudioBlock` (`insertAudioBlock`).
   - Tích hợp giọng đọc nhân tạo Text-to-Speech (TTS).
4. [`bot-recipes.md`](references/bot-recipes.md):
   - Mẫu code hoàn chỉnh chạy được:
     - Recipe 1: Echo & Interactive Command Bot.
     - Recipe 2: Soundboard & Audio Streamer Bot.
     - Recipe 3: Channel Gatekeeper / Welcome Bot.
     - Recipe 4: Xử lý tin nhắn văn bản dài vượt quá 512 ký tự (`buildTextMessage`).
     - Recipe 5: Cấu hình chạy ngầm 24/7 dưới dạng Linux Systemd Service.

### 1.5 Bộ Template Mẫu Sẵn sàng Sử dụng (`resources/templates/`)
- `basic_bot.py`: Khung bot cơ bản xử lý kết nối, đăng nhập, vào kênh và lệnh văn bản.
- `soundboard_bot.py`: Bot phát âm thanh từ thư mục `/sounds` vào phòng TeamTalk.
- `admin_bot.py`: Bot quản trị viên hỗ trợ lệnh kick, ban, di chuyển người dùng, tạo kênh, xem thống kê server.

### 1.6 Master Guide (`SKILL.md`)
- Soạn thảo tại root dự án `SKILL.md` theo chuẩn format Skill của Antigravity/Codex.
- Đồng bộ và cài đặt vào thư mục global: `C:\Users\LCBoy\.gemini\skills\team_talk_bot_developman_skill` để AI agent ở mọi dự án khác đều tự động nhận diện và kích hoạt được skill này.

---

## 2. Kiểm thử & Xác minh (Verification)
1. **Kiểm thử Import TeamTalkPy**:
   - `python -c "import TeamTalk5; print(TeamTalk5.getVersion())"` -> Thành công xuất ra `5.23.0.5209`.
2. **Kiểm thử Script Tự động hóa**:
   - Chạy lệnh `init`, tạo thử dự án `test_dummy_bot`, sau đó chạy lệnh `check` -> Đạt kết quả `SUCCESS: Project structure is complete and operational!`.
3. **Kiểm thử Cài đặt Global**:
   - Chạy script chẩn đoán từ `C:\Users\LCBoy\.gemini\skills\team_talk_bot_developman_skill` -> Chạy chuẩn xác, nhận diện đúng môi trường Python 3.11 64-bit và DLL.

---
*Ghi nhận bởi Antigravity Assistant.*
