import os
import re

# ==========================================
# CẤU HÌNH
# ==========================================
SOURCE_FOLDER = r"C:\Users\Dell Precision 7560\OneDrive\Documents\ToolMTC\ok"
# Dòng thiếu của bạn đây:
OUTPUT_FILE = "VungVangTuTien_DaDanhSoLai.txt" 
# Bạn có muốn bắt đầu từ chương 1 không? Nếu muốn bắt đầu từ số khác hãy sửa ở đây
START_CHAPTER = 351

def rewrite_titles():
    if not os.path.exists(SOURCE_FOLDER):
        print(f"❌ Không tìm thấy thư mục: {SOURCE_FOLDER}")
        return

    # 1. Đọc tất cả các file .txt
    files = sorted([f for f in os.listdir(SOURCE_FOLDER) if f.endswith(".txt")])
    if not files:
        print("❌ Không tìm thấy file .txt nào trong thư mục nguồn!")
        return

    full_content = ""
    for filename in files:
        print(f"📖 Đang đọc: {filename}")
        with open(os.path.join(SOURCE_FOLDER, filename), 'r', encoding='utf-8') as f:
            full_content += f.read() + "\n"

    # 2. Regex tối ưu để tách chương
    # Khớp: "=== Chương ... ===" HOẶC dòng chứa "Truyện Net... Chương ...-..."
    header_pattern = r"(?:===\s*Chương\s+\d+[\-\d]*\s*===|Truyện Net.*?Chương\s+\d+[\-\d]*.*?(?:\n|$))"

    # 3. Tách nội dung
    parts = re.split(header_pattern, full_content, flags=re.IGNORECASE)
    # Lọc bỏ đoạn trống
    parts = [p.strip() for p in parts if p.strip()]

    print(f"🔄 Tìm thấy {len(parts)} phân đoạn chương. Đang bắt đầu ghi đè tiêu đề...")

    # 4. Ghi file
    try:
        with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
            for i, content in enumerate(parts):
                current_num = START_CHAPTER + i
                # Tạo tiêu đề mới đồng nhất
                new_header = f"=== Chương {current_num} ===\n\n"
                f.write(new_header + content + "\n\n" + "-"*50 + "\n\n")

        print("-" * 30)
        print(f"✅ HOÀN THÀNH!")
        print(f"📍 File đã lưu tại: {os.path.abspath(OUTPUT_FILE)}")
        print(f"🚀 Tổng số chương mới: {len(parts)} (Từ {START_CHAPTER} đến {START_CHAPTER + len(parts) - 1})")
    except Exception as e:
        print(f"❌ Lỗi khi ghi file: {e}")

if __name__ == "__main__":
    rewrite_titles()