import time
import os
import re
import queue
import pyperclip
from concurrent.futures import ThreadPoolExecutor
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager

# ==========================================
# 1. CẤU HÌNH HỆ THỐNG
# ==========================================
# Mode1
FOLDER_PATH_LINKS = r"C:\Users\Dell Precision 7560\Downloads\LinkTruyen"
# CHỨC NĂNG MỚI: Chỉ tải những link có chứa slug này
TARGET_STORY_SLUG = "vung-vang-tu-tien-toan-bo-tu-tien-gioi-cung-la-nha-ta"

# Mode2
FOLDER_PATH_TEXT = r"C:\Users\Dell Precision 7560\OneDrive\Documents\MTC\Vững Vàng Tu Tiên, Toàn Bộ Tu Tiên Giới Cũng Là Nhà Ta"

BASE_FILENAME = "Vững Vàng Tu Tiên" 
CHAPS_PER_FILE = 100 
MAX_WORKERS = 5
WAIT_TIME = 6 
HEADLESS = True 

# Danh sách Blacklist lọc rác
BLACKLIST_CONTENT = [
    "Ai bảo hắn tu tiên", "Cỡ chữ: A- A+ | ◑ Giao diện", "Bắt đầu đánh dấu hoang cổ thánh thể",
    "Bắt Đầu Kim Phong Tế Vũ Lâu Chủ, Một Đao Kinh Thiên Hạ",
    "Các ngươi càng tin ta càng thật", "Cao Võ Kỉ Nguyên", "Cẩu Tại Lưỡng Giới Tu Tiên",
    "Cẩu Tại Võ Đạo Thế Giới Thành Thánh", "Cẩu Thả tại Sơ Thánh Ma Môn làm Nhân tài",
    "Cẩu Thả Thành Thánh Nhân, Tiên Quan Triệu Ta Chăm Ngựa", "Chuyện lạ Bắc Tề",
    "Dạ Vô Cương", "Đại Đạo Chi Thượng", "Danh Sách Đường Cái Cầu Sinh: Ta Tại Tận Thế Thăng Cấp Vật Tư",
    "Đều Đã Trọng Sinh, Ai Còn Thi Công Chức?", "Dị Độ Lữ Xá", "Đô Thị Siêu Cấp Y Thánh",
    "Hầm ngục này mọc nấm rồi", "Hoàng Hôn Phân Giới", "Hongkong: Ngươi Hồng Hưng Tử, Từ Thiện Đại Vương Cái Quỷ Gì",
    "Huyền Giám Tiên Tộc", "Khấu Vấn Tiên Đạo", "Không có tiền, tu tiên cái gì?",
    "Lấy Một Long Chi Lực Đánh Bại Toàn Bộ Thế Giới", "Linh Cảnh Hành Giả",
    "Ngày Hôm Ngày Cũng Đang Cố Gắng Làm Ma Đầu", "Người thu hồi xác chết (Vớt Thi Nhân)",
    "Nguyên Thủy Pháp Tắc", "Nhân Đạo Đại Thánh", "Nhân tộc trấn thủ sứ", "Phổ La Chi Chủ",
    "Quang Âm Chi Ngoại", "Sơn Hà Tế", "Sơn Hải Đề Đăng", "Ta có một thân kỹ năng bị động",
    "Ta Lấy Lực Phục Tiên", "Ta Ở Biên Quan Bận Làm Ruộng", "Ta tại tu tiên giới vạn cổ trường thanh",
    "Ta thành tâm ma của nữ ma đầu", "Tạo Hoá Tiên Tộc", "Thái Nhất Đạo Chủ", "Thần Nông Đạo Quân",
    "Thần Thoại Chi Hậu", "Tiên Đạo Phần Cuối", "Tiên Quan Có Lệnh", "Tinh Lộ Tiên Tung",
    "Toàn Dân: Triệu Hoán Sư Yếu? Một Cấp Một Cái Dòng Vàng", "Trận Vấn Trường Sinh",
    "Trở Về Làng Chài Nhỏ 1982", "Trùng sinh thật bình tĩnh (Trùng sinh thực quá thảnh thơi)",
    "Từ hài nhi bắt đầu nhập đạo", "Vạn Cổ Thần Đế", "Xích Tâm Tuần Thiên",
    "Subscribe Login", "KHO TRUYỆN CHỮ", "Kho Truyện Chữ Facebook",
    "Chương trước", "Chương tiếp", "phím mũi tên", "WASD", "Báo lỗi", 
    "Tải Ebook", "Giảm font", "Tăng font", "Mê Truyện Chữ", "đọc tại", 
    "Chúc bạn đọc", "truyenfull", "doctruyenchu", "Skip to content", 
    "Search for", "Chưa có truyện bạn muốn", "Tìm kiếm truyện", "Tàng Kinh Các" , "Danh sách các truyện",
    "Ngày Hôm Ngày Cũng Đang Cố Gắng Làm Ma Đầu","Subscribe","Login","≣ MỤC LỤC Chương sau »"
]

# ==========================================
# 2. CÁC HÀM XỬ LÝ TEXT
# ==========================================

def extract_chapter_number(url):
    # Regex hỗ trợ cả chương lẻ (chuong-10) và chương phụ (chuong-10-1)
    match = re.search(r'chuong-([\d\-]+)', url.lower())
    if match:
        val = match.group(1)
        if '-' in val:
            # Nếu là 10-1 thì trả về 10.1 để sắp xếp
            parts = val.split('-')
            return float(f"{parts[0]}.{parts[1]}")
        return float(val)
    return 999999.0

def clean_chapter_content(raw_text, title_text):
    lines = raw_text.split('\n')
    cleaned_lines = []
    for line in lines:
        line = line.strip()
        if not line: continue
        if any(word.lower() in line.lower() for word in BLACKLIST_CONTENT): continue
        if len(line) < len(title_text) + 10 and title_text.lower() in line.lower(): continue
        if line in ['X', 'A', 'a', '←', '→', '↑', '↓', '«', '»']: continue
        if len(line) < 15 and len(line.split()) <= 2 and not line.startswith(('-', '"', '“')): continue
        cleaned_lines.append(line)
    return "\n\n".join(cleaned_lines)

# ==========================================
# 3. MODE 1: SELENIUM CRAWL
# ==========================================

def setup_driver(driver_path):
    options = Options()
    if HEADLESS: options.add_argument("--headless=new")
    options.add_argument("--window-size=1280,1024")
    options.add_argument("--log-level=3")
    options.add_experimental_option('excludeSwitches', ['enable-logging'])
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36")
    prefs = {"profile.managed_default_content_settings.images": 2}
    options.add_experimental_option("prefs", prefs)
    return webdriver.Chrome(service=Service(driver_path), options=options)

def crawl_worker(worker_id, link_queue, driver_path):
    driver = setup_driver(driver_path)
    worker_results = []
    while not link_queue.empty():
        try:
            url = link_queue.get_nowait()
        except queue.Empty:
            break
        try:
            driver.get(url)
            time.sleep(WAIT_TIME)
            magic_script = """
            let target = document.querySelector('.chapter-c, #chapter-c, .chapter-content, #chapter-content-render') || document.body;
            let leafNodes = [];
            function scan(node) {
                let s = window.getComputedStyle(node);
                if (s.display==='none' || s.fontSize==='0px' || s.visibility==='hidden' || node.tagName==='SCRIPT' || node.tagName==='STYLE') return;
                let hasT = Array.from(node.childNodes).some(c => c.nodeType===3 && c.textContent.trim().length>0);
                if (hasT) {
                    let r = node.getBoundingClientRect();
                    if (r.width > 0 && r.height > 0) {
                        leafNodes.push({t: node.innerText, y: r.top + window.scrollY, x: r.left + window.scrollX, w: r.width});
                    }
                } else {
                    Array.from(node.children).forEach(scan);
                }
            }
            scan(target);
            leafNodes.sort((a, b) => Math.abs(a.y - b.y) < 5 ? a.x - b.x : a.y - b.y);
            let res = "";
            for (let i=0; i<leafNodes.length; i++) {
                let c=leafNodes[i], n=leafNodes[i+1];
                res += c.t;
                if (n) {
                    if (Math.abs(n.y - c.y) > 8) res += "\\n"; 
                    else if (n.x - (c.x + c.w) > 1) res += " "; 
                }
            }
            return {title: document.title, content: res};
            """
            data = driver.execute_script(magic_script)
            clean_text = clean_chapter_content(data['content'], data['title'])
            chap_num = extract_chapter_number(url)
            title_display = data['title'].split('-')[0].strip()
            chapter_output = f"=== {title_display} ===\n\n{clean_text}\n\n{'-'*50}\n\n"
            worker_results.append((chap_num, chapter_output))
            print(f"✅ [W{worker_id}] Xong chương {chap_num}")
        except Exception as e:
            print(f"❌ [W{worker_id}] Lỗi tại: {url}")
        finally:
            link_queue.task_done()
    driver.quit()
    return worker_results

# ==========================================
# 4. MODE 2: COPY CONTENT
# ==========================================

def get_single_chapter_content(chapter_number):
    # ==========================================
    # CẤU HÌNH CÁC PATTERN (ĐÃ CẬP NHẬT)
    # ==========================================
    patterns = [
        # Trường hợp mới: "=== Chương 99 ===" hoặc "--- Chương 99 ---"
        rf"^[=\s-]*Chương\s+{chapter_number}\s*[=\s-]*$",
        
        # Trường hợp 1: "Chương 1:" hoặc "Chương 1 " 
        rf"^\s*Chương\s+{chapter_number}\b",
        
        # Trường hợp 2: "Chương 01" (Dành cho số nhỏ hơn 10)
        rf"^\s*Chương\s+0{chapter_number}\b" if int(chapter_number) < 10 else None,
        
        # Bạn có thể thêm các pattern khác vào đây...
    ]
    # Lọc bỏ các pattern None
    patterns = [p for p in patterns if p]

    # Pattern dùng để tìm điểm kết thúc (Bắt đầu của chương bất kỳ tiếp theo)
    # Cập nhật để nhận diện cả dòng có dấu === làm ranh giới kết thúc
    next_header_pattern = r"^\s*([=\s-]*Chương\s+\d+|Chương\s+\d+)"

    if not os.path.exists(FOLDER_PATH_TEXT):
        print(f"❌ Thư mục không tồn tại: {FOLDER_PATH_TEXT}")
        return None

    for filename in os.listdir(FOLDER_PATH_TEXT):
        if filename.endswith(".txt"):
            file_path = os.path.join(FOLDER_PATH_TEXT, filename)
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                    match_start = None
                    for p in patterns:
                        # Sử dụng re.MULTILINE để ^ khớp với đầu mỗi dòng
                        match_start = re.search(p, content, re.MULTILINE | re.IGNORECASE)
                        if match_start:
                            break 
                    
                    if match_start:
                        start_idx = match_start.start()
                        # Lấy phần nội dung từ sau tiêu đề chương vừa tìm thấy
                        search_limit_idx = match_start.end()
                        remaining_content = content[search_limit_idx:]
                        
                        # Tìm chương kế tiếp để cắt đoạn
                        match_next = re.search(next_header_pattern, remaining_content, re.MULTILINE | re.IGNORECASE)
                        
                        if match_next:
                            end_idx = search_limit_idx + match_next.start()
                            return content[start_idx:end_idx].strip()
                        else:
                            return content[start_idx:].strip()
                            
            except Exception as e:
                print(f"Lỗi đọc file {filename}: {e}")
    return None

def parse_chapters(user_input):
    chapters = []
    if '-' in user_input:
        start, end = map(int, user_input.split('-'))
        chapters = list(range(start, end + 1))
    else:
        parts = re.split(r'[,\s]+', user_input)
        chapters = [int(p) for p in parts if p.isdigit()]
    return sorted(list(set(chapters)))

# ==========================================
# 5. CHƯƠNG TRÌNH CHÍNH
# ==========================================

def main():
    print("=== TOOL QUẢN LÝ TRUYỆN TỔNG HỢP ===")
    print("1. Chế độ CONVERT TEXT (Crawl link từ folder Downloads)")
    print("2. Chế độ COPY CONTENT (Trích xuất từ file MTC và tạo Prompt)")
    mode = input("Chọn chế độ (1/2): ").strip()

    if mode == "1":
        if not os.path.exists(FOLDER_PATH_LINKS):
            print(f"❌ Không tìm thấy thư mục link: {FOLDER_PATH_LINKS}")
            return
        
        chapter_dict = {}
        print(f"🔍 Đang lọc link theo Slug: {TARGET_STORY_SLUG}...")
        
        for filename in os.listdir(FOLDER_PATH_LINKS):
            if filename.endswith(".txt"):
                with open(os.path.join(FOLDER_PATH_LINKS, filename), 'r', encoding='utf-8') as f:
                    # Dùng Regex hốt sạch URL để tránh lỗi dấu phẩy/khoảng trắng
                    raw_links = re.findall(r'https?://[^\s,]+', f.read())
                    
                    for link in raw_links:
                        link = link.strip().strip(',')
                        # CHỨC NĂNG TARGET SLUG:
                        if "chuong-" in link.lower() and TARGET_STORY_SLUG in link.lower():
                            num = extract_chapter_number(link)
                            chapter_dict[num] = link
                            
        sorted_nums = sorted(chapter_dict.keys())
        all_sorted_urls = [chapter_dict[n] for n in sorted_nums]
        
        if not all_sorted_urls:
            print(f"❌ Không tìm thấy link nào khớp với slug: {TARGET_STORY_SLUG}")
            return
            
        print(f"🎯 Tìm thấy {len(all_sorted_urls)} chương hợp lệ. Bắt đầu Crawl...")
        link_queue = queue.Queue()
        for url in all_sorted_urls: link_queue.put(url)
        
        driver_path = ChromeDriverManager().install()
        raw_results = []
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            futures = [executor.submit(crawl_worker, i+1, link_queue, driver_path) for i in range(MAX_WORKERS)]
            for f in futures: raw_results.extend(f.result())
            
        raw_results.sort(key=lambda x: x[0])
        final_contents = [x[1] for x in raw_results]
        
        file_idx = 1
        for i in range(0, len(final_contents), CHAPS_PER_FILE):
            chunk = final_contents[i : i + CHAPS_PER_FILE]
            suffix = f"_{file_idx}" if len(final_contents) > CHAPS_PER_FILE else ""
            out_name = f"{BASE_FILENAME}{suffix}.txt"
            with open(out_name, "w", encoding="utf-8") as f:
                for content in chunk: f.write(content)
            print(f"💾 Đã lưu: {out_name}")
            file_idx += 1
        print("✨ Hoàn thành Mode 1!")

    elif mode == "2":
        # ... (Giữ nguyên logic Mode 2 của bạn)
        print("--- Tool Copy Đa Năng ---")
        while True:
            user_input = input("\nNhập số chương (vd: 1-5, 10) hoặc 'q' thoát: ").strip()
            if user_input.lower() == 'q': break
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
                        f"##trình bày nhiều đoạn tổng khoảng 1000-1200 từ cho mỗi chương, nhớ ghi rõ những thông tin về số liệu, cảnh giới các nhân vật nếu có đề cập\n"
                        f"##ko được bỏ các đoạn hội thoại,\n"
                        f"##phần trình bày của mỗi chương bắt buộc phải có ít nhất 1000 words\n"
                    )
                    final_result = full_content.strip() + footer_prompt
                    pyperclip.copy(final_result)
                    print(f"✅ Đã copy {len(found_chapters)} chương vào Clipboard!")
                else:
                    print("❌ Không tìm thấy chương nào.")
            except Exception as e:
                print(f"Lỗi: {e}")

if __name__ == "__main__":
    main()