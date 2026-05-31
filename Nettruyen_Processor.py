import re
import os
import time
import threading
import pyperclip
from concurrent.futures import ThreadPoolExecutor
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup

# ==============================================================================
# TỔNG HỢP CẤU HÌNH (CHO CẢ 2 CHỨC NĂNG)
# ==============================================================================

# --- Cấu hình Chức năng 1 (Tải truyện) ---
LINK_SOURCE_PATH = r"C:\Users\Dell Precision 7560\Downloads\LinkTruyen"
SAVE_PATH = os.path.dirname(os.path.abspath(__file__))
TARGET_STORY_SLUG = "doc-convert-an-nguoi-tu-tien-gioi-dua-vao-mo-phong-lat-tung-ban-co-39984"
BASE_FILENAME = "Ăn người tu tiên giới, dựa vào mô phỏng lật tung bàn cờ"
CHAPS_PER_FILE = 100
MAX_WORKERS = 3
MAX_RETRIES = 3
RETRY_DELAY = 3

# --- Cấu hình Chức năng 2 (Copy nội dung) ---
FOLDER_PATH_COPY = r"C:\Users\Dell Precision 7560\OneDrive\Documents\MTC\Ăn người tu tiên giới, dựa vào mô phỏng lật tung bàn cờ"

# ==============================================================================
# LOGIC CHỨC NĂNG 1: TẢI TRUYỆN
# ==============================================================================

thread_local = threading.local()

def get_driver():
    if not hasattr(thread_local, "driver"):
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--log-level=3")
        chrome_options.add_argument("--blink-settings=imagesEnabled=false")
        chrome_options.add_argument(f"user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36")
        
        # Khởi tạo driver path (chỉ tải 1 lần hoặc dùng manager)
        service = Service(ChromeDriverManager().install())
        thread_local.driver = webdriver.Chrome(service=service, options=chrome_options)
        thread_local.driver.set_page_load_timeout(30)
    return thread_local.driver

def clean_chapter_content(raw_text, title_text):
    blacklist = {
        "Sư Tôn Mỗi Đêm Đều Muốn Ta Hống Ngủ", "NetTruyen", "NetTruyen.com.vn",
        "NetTruyen - Cập nhật truyện 24h online", "Đọc truyện online 24h",
        "NetTruyen là trang web đọc truyện dịch và convert online miễn phí với hàng vạn đầu truyện được dịch và convert hay nhất từ trước đến nay.",
        "Hỗ trợ mọi thiết bị như di động và máy tính bảng. Tất cả các truyện trên site đều được độc giả sưu tầm từ nhiều nguồn khác nhau, chúng tôi không chịu bất cứ trách nhiệm nào về vấn đề bản quyền tác giả.",
        "Nếu các bạn đọc truyện nào thấy có nội dung liên quan đến vấn đề chính trị hoặc có nội dung không lành mạnh vui lòng liên hệ chúng tôi xóa bỏ truyện khỏi trang web. Chân thành cảm ơn.",
        "2020 - 2026 ©", "Bạn đang đọc truyện tại", "Trang chủ", "Thống Kê", 
        "Truyện mới", "Truyện hot", "Truyện full", "Truyện dịch", "Truyện convert", 
        "Thể loại", "Ngôn Tình", "Đô Thị", "Tiên Hiệp", "Sắc", "Xuyên Không", 
        "Dị Giới", "Kiếm Hiệp", "Võng Du", "Huyền Huyễn", "Khoa Huyễn", "Thám Hiểm", 
        "Dị Năng", "Quan Trường", "Trinh Thám", "Quân Sự", "Cổ Đại", "Sủng", 
        "Trọng Sinh", "Lịch Sử", "Đông Phương", "Hệ Thống", "Nữ Cường", "Cung Đấu", 
        "Đam Mỹ", "Gia Đấu", "Hài Hước", "Truyện Teen", "Linh Dị", "Điền Văn", 
        "Nữ Phụ", "Ngược", "Mạt Thế", "Bách Hợp", "Xuyên Nhanh", "Khác", 
        "Phương Tây", "Light Novel", "Đoản Văn", "Việt Nam", "Dã Sử", "Văn học Việt", 
        "Tiểu Thuyết", "Nhiều Converter", "Review sách", "Tổng Tài", "Mỹ Thực", 
        "Home", "Trước", "List chương", "Sau", "Toàn màn hình", "Nền đen", 
        "Nền trắng", "Danh sách chương", "Đầu", "Cuối", "Close", "truyện hay",
        "- Đọc truyện online", "đọc truyện chữ,", "truyện mới", "kiếm hiệp",
        "Thập Niên 80: Đại Sư Huyền Học Luôn Muốn Ly Hôn",
        "Nhật Ký Trưởng Thành Của Người Dẫn Đường Nhân Tạo",
        "Bề Tôi Đắc Lực - Hoàng Đồng Tả Luân", "Xinh Đẹp - Quân Lai",
        "Đọc truyện Bình Nguyên Cầu Sinh: Ta Mỗi Ngày Đổi Mới Một Cái Tình Báo Nhỏ online",
        "Đọc truyện Bình Nguyên Cầu Sinh: Ta Mỗi Ngày Đổi Mới Một Cái Tình Báo Nhỏ"
    }
    trash_keywords = ["đọc tại", "truyenfull", "Báo lỗi", "Tải Ebook"]
    lines = raw_text.split('\n')
    cleaned_lines = []
    for line in lines:
        line = line.strip()
        if not line or len(line) < 2: continue
        if line.lower() == title_text.lower(): continue
        if line in blacklist: continue
        if re.search(r"Người đăng:", line): continue
        trash_count = sum(1 for word in trash_keywords if word.lower() in line.lower())
        if trash_count > 1: continue 
        cleaned_lines.append(line)
    return "\n\n".join(cleaned_lines)

def process_chapter(url):
    url = url.strip()
    if not url.startswith("http"): return None
    driver = get_driver()
    content_result = None
    for attempt in range(MAX_RETRIES):
        try:
            driver.get(url)
            time.sleep(3)
            soup = BeautifulSoup(driver.page_source, "lxml")
            title = soup.find('h2') or soup.find('h1') or soup.find('a', class_='chapter-title')
            title_text = title.get_text().strip() if title else "Chương không tiêu đề"
            content_box = (
                soup.find('div', class_='chapter-c') or 
                soup.find('div', id='chapter-c') or 
                soup.find('div', class_='chapter-content') or 
                soup.find('div', id='chapter-content')
            )
            if content_box:
                for trash in content_box(["script", "style", "ins", "button", "iframe", "nav", "div.ads"]):
                    trash.decompose()
                raw_text = content_box.get_text("\n")
            else:
                raw_text = soup.get_text("\n")
            final_text = clean_chapter_content(raw_text, title_text)
            if len(final_text) > 400:
                print(f"✅ [Worker {threading.get_ident()}] Đã lấy: {title_text}")
                content_result = f"=== {title_text} ===\n\n{final_text}\n\n{'-'*50}\n\n"
                break 
        except Exception:
            time.sleep(RETRY_DELAY)
    return content_result

def run_crawler():
    print("🚀 Đang khởi tạo hệ thống Driver...")
    chapter_dict = {}
    if not os.path.exists(LINK_SOURCE_PATH):
        print(f"❌ Không thấy folder link: {LINK_SOURCE_PATH}")
        return
    link_files = [f for f in os.listdir(LINK_SOURCE_PATH) if f.endswith(".txt") and "Result" not in f]
    for filename in link_files:
        file_path = os.path.join(LINK_SOURCE_PATH, filename)
        with open(file_path, 'r', encoding='utf-8') as f:
            links = re.split(r'[,\s\n\r]+', f.read())
            for link in links:
                link = link.strip().strip(',')
                if "http" in link and TARGET_STORY_SLUG in link:
                    num_match = re.search(r'-(\d+)/?$', link)
                    if num_match:
                        chapter_dict[int(num_match.group(1))] = link
    sorted_nums = sorted(chapter_dict.keys())
    total_chaps = len(sorted_nums)
    if total_chaps == 0:
        print("❌ Không tìm thấy link!")
        return
    print(f"🎯 Tổng cộng: {total_chaps} chương. Đang xử lý...")
    all_urls = [chapter_dict[n] for n in sorted_nums]
    results = []
    try:
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            results = list(executor.map(process_chapter, all_urls))
    finally:
        print("🧹 Đang hoàn tất quá trình tải...")
    file_idx = 1
    for i in range(0, total_chaps, CHAPS_PER_FILE):
        chunk = results[i : i + CHAPS_PER_FILE]
        save_name = f"{BASE_FILENAME}_{file_idx}.txt"
        save_full_path = os.path.join(SAVE_PATH, save_name)
        try:
            with open(save_full_path, "w", encoding="utf-8") as f:
                for content in chunk:
                    if content: f.write(content)
                f.flush()
                os.fsync(f.fileno())
            print(f"💾 Đã lưu thành công: {save_name}")
        except Exception as e:
            print(f"❌ Lỗi ghi file {save_name}: {e}")
        file_idx += 1
    print("\n✨ HOÀN THÀNH CRAWL!")

# ==============================================================================
# LOGIC CHỨC NĂNG 2: COPY NỘI DUNG (CHỈ SỬA REGEX TẠI ĐÂY)
# ==============================================================================

def get_single_chapter_content(chapter_number):
    # Sử dụng \b hoặc cho phép ký tự không phải số theo sau (như dấu :)
    # Pattern khớp "Chương 4", "Chương 04", "Chương 04:", "=== Chương 04"
    target_pattern = rf"Chương\s+0*{chapter_number}(?!\d)"
    decorated_pattern = rf"={1,}\s*Chương\s+0*{chapter_number}(?!\d)"
    
    next_header_pattern = r"Chương\s+\d+(?!\d)"
    next_decorated_pattern = r"={1,}\s*Chương\s+\d+(?!\d)"

    for filename in os.listdir(FOLDER_PATH_COPY):
        if filename.endswith(".txt"):
            file_path = os.path.join(FOLDER_PATH_COPY, filename)
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                    # Ưu tiên tìm pattern có dấu === trước, nếu không thấy mới tìm pattern thường
                    match_start = re.search(decorated_pattern, content) or re.search(target_pattern, content)
                    
                    if match_start:
                        # Lùi lại để lấy cả các dấu === phía trước nếu có
                        start_idx = match_start.start()
                        remaining_content = content[match_start.end():]
                        
                        # Tìm chương kế tiếp để cắt
                        match_next = re.search(next_decorated_pattern, remaining_content) or re.search(next_header_pattern, remaining_content)
                        
                        if match_next:
                            end_idx = match_start.end() + match_next.start()
                            return content[start_idx:end_idx].strip()
                        else:
                            return content[start_idx:].strip()
            except Exception as e:
                print(f"Lỗi khi đọc file {filename}: {e}")
    return None

def parse_chapters(user_input):
    chapters = []
    if '-' in user_input:
        parts = user_input.split('-')
        if len(parts) == 2 and parts[0].isdigit() and parts[1].isdigit():
            start, end = map(int, parts)
            chapters = list(range(start, end + 1))
    else:
        parts = re.split(r'[,\s]+', user_input)
        chapters = [int(p) for p in parts if p.isdigit()]
    return sorted(list(set(chapters)))

def run_copy_tool():
    print("\n--- Tool Copy Đa Năng ---")
    print("Nhập chương lẻ (1451), danh sách (1451, 1453) hoặc dải (1451-1455)")
    while True:
        user_input = input("\nNhập số chương (hoặc 'b' để quay lại menu): ").strip()
        if user_input.lower() == 'b': break
        try:
            chapter_list = parse_chapters(user_input)
            if not chapter_list: continue
            full_content = ""
            found_chapters = []
            for ch in chapter_list:
                content = get_single_chapter_content(ch)
                if content:
                    full_content += content + "\n\n"
                    found_chapters.append(str(ch))
                else:
                    print(f"⚠️ Không tìm thấy chương {ch}")
            if full_content:
                chaps_str = ", ".join(found_chapters)
                footer_prompt = (
                    f"\n\n\"Đọc chương {chaps_str}, sau đó trình bày chi tiết nội dung với độ chính xác 100% "
                    f"và đầy đủ thông tin tình tiết. Cụ thể là trình bày tất cả không bỏ sót gì, "
                    f"theo phong cách copy paste nội dung từ file văn bản gốc ra và thuật lại thành các đoạn lớn "
                    f"để đọc nhanh hơn, giữ lại 80% chữ quan trọng, và các đoạn hội thoại có thể được rút ngắn súc tích\n"
                    f"##trình bày nhiều đoạn tổng khoảng 700-1000 từ cho mỗi chương\n"
                    f"##phần trình bày của mỗi chương bắt buộc phải có ít nhất 700-1000 words\n"
                    f"##sau khi trình bày xong hết, hãy đưa ra gợi ý tôi nên đọc full chương nào đó, điều kiện là nó có tình tiết hay, thú vị,lạ (có thể theo hướng hắc ám hoặc tích cực)\""
                )
                final_result = full_content.strip() + footer_prompt
                pyperclip.copy(final_result)
                print(f"✅ Đã copy {len(found_chapters)} chương vào Clipboard!")
            else:
                print("❌ Không tìm thấy chương nào.")
        except Exception as e:
            print(f"Có lỗi xảy ra: {e}")

# ==============================================================================
# MENU CHÍNH
# ==============================================================================

if __name__ == "__main__":
    while True:
        print("\n" + "="*40)
        print("CHƯƠNG TRÌNH QUẢN LÝ TRUYỆN")
        print("="*40)
        print("1. Chạy Crawl truyện (Tải từ link)")
        print("2. Chạy Tool Copy nội dung (Clipboard)")
        print("q. Thoát chương trình")
        
        choice = input("\nChọn chức năng (1/2/q): ").strip().lower()
        
        if choice == '1':
            run_crawler()
        elif choice == '2':
            run_copy_tool()
        elif choice == 'q':
            print("Đang thoát...")
            break
        else:
            print("Lựa chọn không hợp lệ, vui lòng chọn lại.")