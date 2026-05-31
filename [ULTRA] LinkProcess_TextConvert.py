import requests
from bs4 import BeautifulSoup
import re
import os
import time
from concurrent.futures import ThreadPoolExecutor

# ==========================================
# 1. CẤU HÌNH HỆ THỐNG
# ==========================================
# THAY ĐỔI TẠI ĐÂY: Nhập đường dẫn thư mục chứa các file txt
FOLDER_PATH = r"C:\Users\Dell Precision 7560\Downloads\LinkTruyen"

TARGET_STORY_SLUG = "khung-bo-song-lai"
BASE_FILENAME = "Khủng Bố Sống Lại" 
CHAPS_PER_FILE = 50 
MAX_WORKERS = 10
MAX_RETRIES = 5 
RETRY_DELAY = 2 
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"}

# ==========================================
# 2. HÀM LỌC NỘI DUNG (GIỮ NGUYÊN)
# ==========================================
def clean_chapter_content(raw_text, title_text):
    # 1. Cắt bỏ các phần rác lớn ở đầu và cuối trang dựa trên từ khóa chặn
    cutoff_keywords = [
        "Truyện Hot Mới", "Danh sách chương", "Bình luận", "Cài đặt giao diện",
        "Sử dụng mũi tên trái", "Sử dụng phím mũi tên", "Danh Sách Chương", 
        "Sắp Xếp", "Mới nhất", "Cũ nhất", "Tặng Quà", "Đề Cử"
    ]
    for kw in cutoff_keywords:
        if kw in raw_text:
            raw_text = raw_text.split(kw)[0]

    lines = raw_text.split('\n')
    cleaned_lines = []
    
    # 2. Danh sách đen chứa các cụm từ xuất hiện trên giao diện web
    blacklist = [
        "Chương trước", "Chương tiếp", "phím mũi tên", "WASD", "Báo lỗi", 
        "Tải Ebook", "Giảm font", "Tăng font", "Mê Truyện Chữ", "đọc tại", 
        "Chúc bạn đọc", "truyenfull", "Home", "Linh Dị", "Huyền Huyễn", 
        "Sửa Chương", "Cài Đặt", "Tặng Quà", "Động Lực", "Đề Cử", 
        "Tiếp »", "« Trước", "Vô Hạn Lưu", "Thế Giới Ngoài Và Trong",
        "Mục lục", "Tải App"
    ]

    for line in lines:
        line = line.strip()
        
        # Loại bỏ dòng trống
        if not line: continue
        
        # A. Loại bỏ nếu dòng chứa từ khóa trong blacklist (không phân biệt hoa thường)
        if any(word.lower() in line.lower() for word in blacklist): continue
        
        # B. Loại bỏ dòng trùng với tiêu đề chương (tránh lặp tiêu đề)
        if line.lower() == title_text.lower(): continue
        
        # C. Loại bỏ các ký tự điều hướng đơn lẻ
        if line in ['X', 'A', 'a', '←', '→', '«', '»', '↑', '↓']: continue
        
        # D. NÂNG CẤP: Dùng Regex để loại bỏ các dòng báo số chữ (ví dụ: "614 Chữ", "1878 Chữ")
        if re.search(r'^\d+\s*[Cc]hữ$', line): continue
        
        # E. NÂNG CẤP: Loại bỏ tên riêng lẻ hoặc dòng menu quá ngắn (như Rose, Cài Đặt)
        # Chỉ giữ lại nếu dòng đó bắt đầu bằng dấu hội thoại hoặc là câu dài (thường > 10 ký tự)
        if line == "Rose" or line == "Cài Đặt": continue
        if len(line) < 10 and not line.startswith(('-', '"', '“', '「')):
            # Nếu chỉ có 1-2 từ và quá ngắn thì khả năng cao là rác menu
            if len(line.split()) <= 2: continue

        cleaned_lines.append(line)
        
    return "\n\n".join(cleaned_lines)

# ==========================================
# 3. HÀM XỬ LÝ TẢI CHƯƠNG (GIỮ NGUYÊN)
# ==========================================
def extract_chapter_number(url):
    match = re.search(r'chuong-(\d+)', url.lower()) # chuong/[num]
    # return int(match.group(1)) if match else None
    # match = re.search(r'-(\d+)/?$', url.strip())
    # match = re.search(r'chuong+(\d+)', url.lower())  # chuong-[num]
    return int(match.group(1)) if match else None

def process_chapter(url):
    url = url.strip()
    if not url.startswith("http"): return None
    
    for attempt in range(MAX_RETRIES):
        try:
            resp = requests.get(url, headers=HEADERS, timeout=15)
            resp.encoding = resp.apparent_encoding
            
            if "An error occurred" in resp.text or resp.status_code != 200:
                time.sleep(RETRY_DELAY * (attempt + 1))
                continue

            soup = BeautifulSoup(resp.text, "lxml")
            title = soup.find('h2') or soup.find('h1') or soup.find('a', class_='chapter-title')
            title_text = title.get_text().strip() if title else "Chuong Moi"

            content_box = soup.find('div', class_='chapter-c') or \
                          soup.find('div', id='chapter-c') or \
                          soup.find('div', class_='chapter-content') or \
                          soup.find('div', id='chapter-content') or \
                          soup.find('div', class_='content-inner') or \
                          soup.find('div', class_=re.compile(r'reading-content|chapter-wrapper'))

            if content_box:
                for trash in content_box(["script", "style", "ins", "button", "iframe", "nav"]):
                    trash.decompose()
                raw_text = content_box.get_text("\n")
            else:
                for tag in soup(["script", "style", "header", "footer", "nav", "aside", "button"]):
                    tag.decompose()
                raw_text = soup.get_text("\n")

            if len(raw_text) < 200 or "An error occurred" in raw_text:
                time.sleep(RETRY_DELAY)
                continue
            
            final_text = clean_chapter_content(raw_text, title_text)
            print(f"✅ Xong: {title_text}")
            return f"=== {title_text} ===\n\n{final_text}\n\n{'-'*50}\n\n"
        
        except Exception:
            time.sleep(RETRY_DELAY)
            
    return f"❌ LỖI VĨNH VIỄN: {url}\n\n"

# ==========================================
# 4. LUỒNG CHẠY CHÍNH (ĐÃ ĐỔI SANG PATH FOLDER)
# ==========================================
def main():
    chapter_dict = {}
    
    if not os.path.exists(FOLDER_PATH):
        print(f"❌ Không tìm thấy thư mục: {FOLDER_PATH}")
        return

    print(f"🔍 Đang quét toàn bộ file trong thư mục: {FOLDER_PATH}")
    
    # Duyệt qua tất cả các file trong thư mục
    for filename in os.listdir(FOLDER_PATH):
        if filename.endswith(".txt"):
            file_path = os.path.join(FOLDER_PATH, filename)
            with open(file_path, 'r', encoding='utf-8') as f:
                links = re.split(r'[,\s\n\r]+', f.read())
                for link in links:
                    link = link.strip().strip(',')
                    if "http" in link and TARGET_STORY_SLUG in link:
                        num = extract_chapter_number(link)
                        if num: chapter_dict[num] = link

    sorted_nums = sorted(chapter_dict.keys())
    total_chaps = len(sorted_nums)
    if total_chaps == 0:
        print("❌ Không tìm thấy link nào hợp lệ trong thư mục này!")
        return

    print(f"🎯 Tổng hợp được {total_chaps} chương duy nhất. Bắt đầu tải đa luồng...")

    all_urls = [chapter_dict[n] for n in sorted_nums]
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        results = list(executor.map(process_chapter, all_urls))

    print(f"📦 Đang chia nhỏ thành các file {CHAPS_PER_FILE} chương...")
    file_idx = 1
    for i in range(0, total_chaps, CHAPS_PER_FILE):
        chunk = results[i : i + CHAPS_PER_FILE]
        suffix = f" {file_idx}" if file_idx > 1 else ""
        filename = f"{BASE_FILENAME}{suffix}.txt"
        
        with open(filename, "w", encoding="utf-8") as f:
            for content in chunk:
                if content: f.write(content)
        
        print(f"💾 Đã lưu: {filename}")
        file_idx += 1

    print("\n✨ HOÀN THÀNH TẤT CẢ!")

if __name__ == "__main__":
    main()