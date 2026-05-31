import time
import os
import re
import queue
from concurrent.futures import ThreadPoolExecutor
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager

# ==========================================
# 1. CẤU HÌNH HỆ THỐNG
# ==========================================
# THAY ĐỔI TẠI ĐÂY: Đường dẫn thư mục chứa các file txt link
FOLDER_PATH = r"C:\Users\Dell Precision 7560\Downloads\LinkTruyen"

TARGET_STORY_SLUG = "khung-bo-song-lai"
BASE_FILENAME = "Khủng Bố Sống Lại" 
CHAPS_PER_FILE = 100 

MAX_WORKERS = 10      # Số trình duyệt chạy cùng lúc
WAIT_TIME = 4      # Thời gian chờ trang tải xong (giây)
HEADLESS = True      # True: Ẩn trình duyệt, False: Hiện trình duyệt

# ==========================================
# 2. XỬ LÝ TEXT & TRÍCH XUẤT
# ==========================================

def extract_chapter_number(url):
    # Đã sửa để khớp với link dạng /chuong/1
    match = re.search(r'chuong-(\d+)', url.lower())
    return int(match.group(1)) if match else 999999

def clean_chapter_content(raw_text, title_text):
    cutoff_keywords = ["Truyện Hot Mới", "Danh sách chương", "Bình luận", "Cài đặt giao diện", "Bạn có thể dùng phím mũi tên"]
    for kw in cutoff_keywords:
        if kw in raw_text:
            raw_text = raw_text.split(kw)[0]

    lines = raw_text.split('\n')
    cleaned_lines = []
    
    blacklist = [
        "Chương trước", "Chương tiếp", "phím mũi tên", "WASD", "Báo lỗi", 
        "Tải Ebook", "Giảm font", "Tăng font", "Mê Truyện Chữ", "đọc tại", 
        "Chúc bạn đọc", "truyenfull", "nguồn:", "vui lòng không copy"
    ]

    for line in lines:
        line = line.strip()
        if not line: continue
        if any(word.lower() in line.lower() for word in blacklist): continue
        # Loại bỏ dòng lặp lại tiêu đề
        if title_text.lower() in line.lower() or line.lower() in title_text.lower(): continue
        if line in ['X', 'A', 'a', '←', '→', '↑', '↓']: continue
        cleaned_lines.append(line)
        
    return "\n\n".join(cleaned_lines)

# ==========================================
# 3. SELENIUM WORKER
# ==========================================

def setup_driver(driver_path):
    options = Options()
    if HEADLESS: options.add_argument("--headless=new")
    options.add_argument("--window-size=1280,1024")
    options.add_argument("--log-level=3")
    options.add_experimental_option('excludeSwitches', ['enable-logging'])
    # Không tải ảnh để chạy nhanh hơn
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
            
            # Script lấy text sạch từ trình duyệt (Trị lỗi font)
            magic_script = """
            let target = document.querySelector('.chapter-c, #chapter-c, .chapter-content, .content-ct, #content-chapter') || document.body;
            let leafNodes = [];
            function scan(node) {
                let s = window.getComputedStyle(node);
                if (s.display==='none' || s.fontSize==='0px' || s.visibility==='hidden') return;
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
            
            chapter_output = f"=== {data['title']} ===\n\n{clean_text}\n\n{'-'*50}\n\n"
            chap_num = extract_chapter_number(url)
            worker_results.append((chap_num, chapter_output))
            
            print(f"✅ W{worker_id} xong chương {chap_num}")
            
        except Exception as e:
            print(f"❌ W{worker_id} lỗi tại: {url}")
        finally:
            link_queue.task_done()
            
    driver.quit()
    return worker_results

# ==========================================
# 4. MAIN PROGRAM
# ==========================================

def main():
    if not os.path.exists(FOLDER_PATH):
        print(f"❌ Không tìm thấy thư mục: {FOLDER_PATH}")
        return

    chapter_dict = {}
    print(f"🔍 Đang quét toàn bộ file .txt trong: {FOLDER_PATH}")
    
    for filename in os.listdir(FOLDER_PATH):
        if filename.endswith(".txt"):
            file_path = os.path.join(FOLDER_PATH, filename)
            with open(file_path, 'r', encoding='utf-8') as f:
                raw_data = f.read()
                raw_links = re.split(r'[,\s\n\r]+', raw_data)
                for link in raw_links:
                    link = link.strip().strip(',')
                    if "http" in link and TARGET_STORY_SLUG in link:
                        num = extract_chapter_number(link)
                        chapter_dict[num] = link

    sorted_nums = sorted(chapter_dict.keys())
    all_sorted_urls = [chapter_dict[n] for n in sorted_nums]
    total_chaps = len(all_sorted_urls)
    
    if total_chaps == 0:
        print("❌ Không tìm thấy link hợp lệ nào trong folder!")
        return
        
    link_queue = queue.Queue()
    for url in all_sorted_urls:
        link_queue.put(url)

    print(f"🎯 Tổng cộng tìm thấy: {total_chaps} chương.")
    driver_path = ChromeDriverManager().install()

    w = min(MAX_WORKERS, total_chaps)
    print(f"🔥 Đang chạy {w} trình duyệt song song...")
    start_time = time.time()
    
    raw_results = []
    with ThreadPoolExecutor(max_workers=w) as executor:
        futures = [executor.submit(crawl_worker, i+1, link_queue, driver_path) for i in range(w)]
        for f in futures:
            raw_results.extend(f.result())

    # Sắp xếp lại theo đúng số chương trước khi lưu
    raw_results.sort(key=lambda x: x[0])
    final_contents = [x[1] for x in raw_results]
    
    print(f"📦 Đang lưu thành các file {CHAPS_PER_FILE} chương...")
    file_idx = 1
    for i in range(0, len(final_contents), CHAPS_PER_FILE):
        chunk = final_contents[i : i + CHAPS_PER_FILE]
        suffix = f" {file_idx}" if file_idx > 1 else ""
        filename = f"{BASE_FILENAME}{suffix}.txt"
        with open(filename, "w", encoding="utf-8") as f:
            for content in chunk: f.write(content)
        print(f"💾 Đã lưu: {filename}")
        file_idx += 1

    print(f"\n✨ HOÀN THÀNH! Tổng thời gian: {int(time.time() - start_time)} giây.")

if __name__ == "__main__":
    main()