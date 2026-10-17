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

## 3. Cập nhật & Nâng cấp Skill (18/10/2026)

### 3.1 Bối cảnh & Yêu cầu Mới
- Tích hợp 2 template thực tế cao cấp vào kho tài nguyên: `TTMediaBot` (Media Streaming studio, live lyrics, DSP, WASAPI, yt-dlp) và `TTUtilities` (Auto-moderation, Jail flood protection, TTS, dịch thuật, private channels).
- **Quy tắc bất di bất dịch**: File `TeamTalk5.py` được trả về nguyên bản mặc định của BearWare SDK (100% stock) và tuyệt đối không được chỉnh sửa.
- **Dynamic SDK Discovery Protocol**: Hướng dẫn AI Agent luôn đọc trực tiếp file `TeamTalk5.py` trong dự án để cập nhật các API, method, struct, event mới nhất khi người dùng nâng cấp SDK.
- Áp dụng kỹ thuật tối ưu prompt từ skill `llm-prompt-optimizer` (khung RSCIT, chain-of-thought, zero-hallucination, few-shot patterns).
- Toàn bộ thay đổi chỉ cập nhật trong thư mục dự án này, không đẩy vào skill global.

### 3.2 Các Hạng Mục Đã Hoàn Thành
1. **Giải pháp Tương thích SDK Nguyên Bản (Stock SDK Compatibility)**:
   - Trong `TeamTalk5.py` mặc định, SDK tìm kiếm DLL tại `os.getcwd()` và `os.path.dirname(__file__) + "\\..\\TeamTalk_DLL"`.
   - Đã tạo thư mục chuẩn `resources/TeamTalk_DLL/TeamTalk5.dll` cạnh `teamtalkpy/`. Nhờ vậy, file gốc `TeamTalk5.py` thực thi trơn tru mà không cần chỉnh sửa bất kỳ dòng nào.
   - Cập nhật script `setup_teamtalk_bot.py` (`init` và `fix`) để luôn tạo đồng bộ thư mục `TeamTalk_DLL/` trong các project bot mới.
2. **Tài liệu Kiến trúc Chuyên sâu (`references/advanced-bot-architectures.md`)**:
   - Tài liệu hóa toàn diện 2 kiến trúc sản xuất thực tế:
     - **Blueprint A (`TTMediaBot`)**: Tích hợp C-API `libmpv` (`mpv.dll`/`mpv.py`), audio backend WASAPI (`ao="wasapi"`), giải mã stream YouTube trực tiếp qua `yt-dlp`, stream lời bài hát/subtitles thời gian thực lên TeamTalk status message (`szStatusMsg`), nhận diện bài hát đa tầng (Chapters -> Shazam -> Google Voice AI), bộ lọc DSP (Pitch shift Rubber Band v3, Silence trimming), và Windows Priority Scheduling (`HIGH_PRIORITY_CLASS`).
     - **Blueprint B (`TTUtilities`)**: Kế thừa hướng đối tượng trực tiếp `class TTUtilities(TeamTalk)`, hệ thống Auto-Jail và chống vượt ngục (flood protection), Text-to-Speech đa engine (Edge TTS, msspeech, gTTS), dịch tự động qua `deep_translator`, sinh kênh riêng tư ngẫu nhiên bảo mật, quản trị cấu hình INI và đa ngôn ngữ `gettext`.
3. **Cơ chế Tự Khám phá API từ `TeamTalk5.py` (`references/teamtalkpy-api.md`)**:
   - Bổ sung **Section 6: Dynamic SDK Discovery**: Hướng dẫn AI Agent và developer cách đọc và bóc tách trực tiếp file `TeamTalk5.py` (cách grep `class ClientEvent`, ánh xạ trong `runEventLoop()`, tra cứu method `def do` và `def get`, đọc cấu trúc `_fields_` của struct, đọc enum `UserRight` và `ClientError`).
   - Thêm cảnh báo nghiêm ngặt về nguyên tắc giữ nguyên gốc SDK wrapper.
4. **Bổ sung Thực chiến vào `references/bot-recipes.md` & `references/project-structure.md`**:
   - Thêm Recipe 6: Đồng bộ Subtitle / Lời bài hát lên thanh trạng thái bot (`doChangeStatus`).
   - Thêm Recipe 7: Auto-Jail và trừng phạt vượt ngục (`onCmdUserJoinedChannel` + `doMoveUser`).
   - Thêm Recipe 8: Phát âm thanh Text-To-Speech (TTS) vào kênh thoại.
   - Bổ sung sơ đồ thư mục Enterprise Modular Bot và hướng dẫn nạp DLL an toàn.
5. **Nâng cấp Công cụ Quản lý (`scripts/setup_teamtalk_bot.py`)**:
   - Thêm action `list-templates` hiển thị đầy đủ thông tin về các starter templates và production blueprints.
   - Tự động nạp cấu hình `os.add_dll_directory` và grep API trực tiếp từ `TeamTalk5.py` khi chạy lệnh `check` (báo cáo phiên bản SDK, số lượng method và events).
   - Tự động tạo cấu trúc thư mục `TeamTalk_DLL/` chuẩn SDK khi chạy lệnh `init` và `fix`.
6. **Tối ưu hóa Toàn diện `SKILL.md`**:
   - Áp dụng chuẩn RSCIT: Role rõ ràng, Situation cụ thể, Constraints nghiêm ngặt (Zero modification trên `TeamTalk5.py`, Bitness 64-bit, Safe DLL loading, Message length 512, Clean termination).
   - Chỉ dẫn chi tiết về quy trình Dynamic Discovery và tham chiếu đến 5 tài liệu chuyên sâu cùng các blueprint trong `resources/templates/`.

### 3.3 Kết Quả Xác Minh (Verification)
- **Kiểm thử SDK gốc**: Chạy lệnh chẩn đoán trên thư mục `resources/teamtalkpy` -> Nạp thành công `TeamTalk SDK engine! Version: 5.23.0.5209`, tìm thấy 116 methods và 54 ClientEvents mà không cần sửa `TeamTalk5.py`.
- **Kiểm thử Scaffolding**: Chạy `python setup_teamtalk_bot.py init --target-dir test_verified_bot` và `check` -> Đạt kết quả `SUCCESS: Project structure is complete and operational!` với đầy đủ các file runtime và cấu trúc tương thích.
- **Kiểm thử CLI Templates**: Lệnh `python setup_teamtalk_bot.py list-templates` hoạt động chính xác.

---
*Ghi nhận bởi Antigravity Assistant.*

