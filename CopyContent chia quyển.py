import os
import re
import pyperclip

# Cấu hình đường dẫn thư mục chứa các file Quyển 01.txt, Quyển 02.txt...
FOLDER_PATH = r"C:\Users\Dell Precision 7560\OneDrive\Documents\MTC\Vô Hạn Khủng Bố"

def get_vol_file_path(vol_number):
    """Tìm đường dẫn file .txt tương ứng với số quyển"""
    vol_pattern = re.compile(rf"Quyển\s+0?{vol_number}|Q0?{vol_number}", re.IGNORECASE)
    for filename in os.listdir(FOLDER_PATH):
        if filename.endswith(".txt") and vol_pattern.search(filename):
            return os.path.join(FOLDER_PATH, filename)
    return None

def get_single_chapter_content(vol_number, chap_number):
    """Tìm nội dung chương, bỏ qua phần mục lục ở đầu file"""
    file_path = get_vol_file_path(vol_number)
    if not file_path:
        return None

    target_header = rf"Chương\s+{chap_number}(?!\d)"
    next_header_pattern = r"Chương\s+\d+(?!\d)"
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
            # Tìm tất cả các vị trí xuất hiện của "Chương X"
            matches = list(re.finditer(target_header, content))
            
            if not matches:
                return None
            
            # Nếu có nhiều hơn 1 vị trí (thường là 1 ở mục lục, 1 ở nội dung), lấy vị trí cuối cùng
            # Nếu chỉ có 1 vị trí, lấy luôn vị trí đó
            best_match = matches[-1]
            start_idx = best_match.start()
            
            remaining = content[best_match.end():]
            
            # Tìm chương kế tiếp để cắt đoạn (cũng phải tìm vị trí thực sự ở nội dung)
            # Ta tìm từ vị trí hiện tại trở đi
            match_next = re.search(next_header_pattern, remaining)
            
            if match_next:
                end_idx = best_match.end() + match_next.start()
                return content[start_idx:end_idx].strip()
            else:
                return content[start_idx:].strip()
                
    except Exception as e:
        print(f"Lỗi khi đọc file Quyển {vol_number}: {e}")
    return None

def parse_input(user_input):
    tasks = []
    parts = re.split(r',\s*', user_input)
    for p in parts:
        if '-' in p and '.' in p:
            vol_part, chap_range = p.split('.')
            try:
                start_ch, end_ch = map(int, chap_range.split('-'))
                for c in range(start_ch, end_ch + 1):
                    tasks.append((int(vol_part), c))
            except: continue
        elif '.' in p:
            try:
                vol, chap = map(int, p.split('.'))
                tasks.append((vol, chap))
            except: continue
    return tasks

def main():
    print("--- Tool Copy (Fix lỗi dính Mục lục) ---")
    print("Ví dụ nhập: 1.1-7 (Sẽ lấy từ Chương 1 đến 7 của Quyển 1)")
    
    while True:
        user_input = input("\nNhập yêu cầu (hoặc 'q' để thoát): ").strip()
        if user_input.lower() == 'q': break
            
        try:
            task_list = parse_input(user_input)
            if not task_list: 
                print("❌ Định dạng không hợp lệ.")
                continue

            full_content = ""
            found_labels = []
            missing_labels = []

            print("🔍 Đang trích xuất nội dung (đang bỏ qua mục lục)...")

            for vol, ch in task_list:
                content = get_single_chapter_content(vol, ch)
                if content and len(content) > 100: # Kiểm tra độ dài để tránh lấy nhầm dòng mục lục ngắn
                    full_content += content + "\n\n" + ("="*30) + "\n\n"
                    found_labels.append(f"Q{vol}-Ch{ch}")
                else:
                    missing_labels.append(f"Q{vol}-Ch{ch}")

            if missing_labels:
                print(f"⚠️ Không tìm thấy nội dung thực của: {', '.join(missing_labels)}")

            if full_content:
                chaps_str = ", ".join(found_labels)
                footer_prompt = (
                    f"\n\n\"Đọc {chaps_str}, sau đó trình bày chi tiết nội dung với độ chính xác 100% "
                    f"và đầy đủ thông tin tình tiết. Cụ thể là trình bày tất cả không bỏ sót gì, "
                    f"theo phong cách copy paste nội dung từ file văn bản gốc ra và thuật lại thành các đoạn lớn "
                    f"để đọc nhanh hơn, giữ lại 80% chữ quan trọng, và các đoạn hội thoại có thể được rút ngắn súc tích\n"
                    f"##trình bày nhiều đoạn tổng khoảng 700-1000 từ cho mỗi chương\n"
                    f"##phần trình bày của mỗi chương bắt buộc phải có ít nhất 700-1000 words\n"
                    f"##sau khi trình bày xong hết, hãy đưa ra gợi ý tôi nên đọc full chương nào đó, điều kiện là nó có tình tiết hay, thú vị,lạ (có thể theo hướng hắc ám hoặc tích cực)\""
                )
                
                final_result = full_content.strip() + footer_prompt
                pyperclip.copy(final_result)
                print(f"✅ Đã xử lý xong! Đã copy {len(found_labels)} chương vào Clipboard.")
            else:
                print("❌ Không lấy được nội dung chương nào.")
                
        except Exception as e:
            print(f"Có lỗi hệ thống xảy ra: {e}")

if __name__ == "__main__":
    main()