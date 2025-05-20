import tkinter as tk
from tkinter import filedialog, scrolledtext, messagebox
import requests
from bs4 import BeautifulSoup
import os
import threading
import time
from urllib.parse import urljoin, urlparse

class PaperDownloaderApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Trình Tải Bài Báo Tự Động")
        self.root.geometry("700x550") # Kích thước cửa sổ

        # Biến lưu trữ
        self.url_var = tk.StringVar()
        self.download_dir_var = tk.StringVar(value=os.getcwd()) # Mặc định là thư mục hiện tại

        # --- Giao diện người dùng ---

        # Khung URL
        url_frame = tk.Frame(root, pady=10)
        url_frame.pack(fill=tk.X)

        tk.Label(url_frame, text="URL Trang Web:", width=15, anchor="w").pack(side=tk.LEFT, padx=5)
        self.url_entry = tk.Entry(url_frame, textvariable=self.url_var, width=60)
        self.url_entry.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=5)
        # Gợi ý URL
        self.url_entry.insert(0, "https.openaccess.thecvf.com/CVPR2023?day=all")


        # Khung Thư mục tải về
        dir_frame = tk.Frame(root, pady=5)
        dir_frame.pack(fill=tk.X)

        tk.Label(dir_frame, text="Thư mục lưu:", width=15, anchor="w").pack(side=tk.LEFT, padx=5)
        self.dir_entry = tk.Entry(dir_frame, textvariable=self.download_dir_var, width=50)
        self.dir_entry.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=5)
        self.browse_button = tk.Button(dir_frame, text="Chọn thư mục", command=self.choose_directory)
        self.browse_button.pack(side=tk.LEFT, padx=5)

        # Nút Bắt đầu tải
        self.download_button = tk.Button(root, text="Bắt đầu tải", command=self.start_download_thread, bg="lightblue", fg="black", height=2, width=15)
        self.download_button.pack(pady=10)

        # Khu vực hiển thị log/trạng thái
        tk.Label(root, text="Trạng thái và Log:").pack(pady=(10,0))
        self.log_area = scrolledtext.ScrolledText(root, wrap=tk.WORD, height=15, width=80)
        self.log_area.pack(pady=5, padx=10, expand=True, fill=tk.BOTH)
        self.log_area.configure(state='disabled') # Chỉ đọc

        # Thanh trạng thái
        self.status_var = tk.StringVar()
        self.status_bar = tk.Label(root, textvariable=self.status_var, bd=1, relief=tk.SUNKEN, anchor=tk.W)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        self.status_var.set("Sẵn sàng")

    def log_message(self, message, level="INFO"):
        """Ghi thông báo vào khu vực log và cập nhật thanh trạng thái."""
        self.log_area.configure(state='normal')
        self.log_area.insert(tk.END, f"[{level}] {message}\n")
        self.log_area.configure(state='disabled')
        self.log_area.see(tk.END) # Cuộn xuống dòng cuối cùng
        if level != "DEBUG": # Không hiển thị DEBUG trên status bar
            self.status_var.set(message.split('\n')[0]) # Hiển thị dòng đầu tiên của thông báo
        self.root.update_idletasks() # Cập nhật UI ngay lập tức

    def choose_directory(self):
        """Mở hộp thoại để chọn thư mục lưu file."""
        directory = filedialog.askdirectory()
        if directory:
            self.download_dir_var.set(directory)
            self.log_message(f"Đã chọn thư mục lưu: {directory}", "DEBUG")

    def start_download_thread(self):
        """Chạy quá trình tải xuống trong một luồng riêng để không làm treo UI."""
        url = self.url_var.get()
        download_dir = self.download_dir_var.get()

        if not url:
            messagebox.showerror("Lỗi", "Vui lòng nhập URL trang web.")
            return
        if not download_dir:
            messagebox.showerror("Lỗi", "Vui lòng chọn thư mục lưu.")
            return

        # Kiểm tra xem URL có hợp lệ không (kiểm tra sơ bộ)
        parsed_url = urlparse(url)
        if not all([parsed_url.scheme, parsed_url.netloc]):
            messagebox.showerror("Lỗi", "URL không hợp lệ. Vui lòng nhập URL đầy đủ (ví dụ: http://...).")
            return

        # Vô hiệu hóa nút tải trong khi xử lý
        self.download_button.config(state=tk.DISABLED, text="Đang tải...")
        self.log_area.configure(state='normal')
        self.log_area.delete(1.0, tk.END) # Xóa log cũ
        self.log_area.configure(state='disabled')

        # Tạo thư mục nếu chưa tồn tại
        os.makedirs(download_dir, exist_ok=True)

        # Chạy download_papers trong một thread mới
        thread = threading.Thread(target=self.download_papers, args=(url, download_dir))
        thread.daemon = True # Thread sẽ tự động kết thúc khi chương trình chính thoát
        thread.start()

    def download_papers(self, page_url, download_dir):
        """
        Tải các bài báo PDF từ URL đã cho.
        """
        self.log_message(f"Bắt đầu quá trình tải từ: {page_url}")
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            # Lấy nội dung trang web
            self.log_message("Đang lấy nội dung trang web...")
            response = requests.get(page_url, headers=headers, timeout=30)
            response.raise_for_status() # Ném lỗi nếu mã trạng thái HTTP là 4xx/5xx
            self.log_message("Đã lấy nội dung trang web thành công.")

            soup = BeautifulSoup(response.content, 'html.parser')

            # Tìm tất cả các thẻ <a> có chứa liên kết đến file PDF
            # Điều chỉnh selector này tùy theo cấu trúc của trang web mục tiêu
            # Ví dụ cho openaccess.thecvf.com: các link PDF thường có trong href và kết thúc bằng .pdf
            pdf_links = []
            for link in soup.find_all('a', href=True):
                href = link['href']
                if href.lower().endswith('.pdf'):
                    # Tạo URL tuyệt đối nếu link là tương đối
                    full_url = urljoin(page_url, href)
                    pdf_links.append(full_url)
            
            # Loại bỏ các link trùng lặp
            pdf_links = sorted(list(set(pdf_links)))


            if not pdf_links:
                self.log_message("Không tìm thấy liên kết PDF nào trên trang.", "WARNING")
                messagebox.showwarning("Thông báo", "Không tìm thấy liên kết PDF nào trên trang được cung cấp.")
                self.download_button.config(state=tk.NORMAL, text="Bắt đầu tải")
                return

            self.log_message(f"Tìm thấy {len(pdf_links)} liên kết PDF tiềm năng.")
            
            downloaded_count = 0
            failed_count = 0

            for i, pdf_url in enumerate(pdf_links):
                try:
                    # Lấy tên file từ URL
                    file_name = os.path.basename(urlparse(pdf_url).path)
                    if not file_name: # Nếu không có path, thử lấy từ phần cuối của URL
                        file_name = pdf_url.split('/')[-1]
                        if '?' in file_name: # Loại bỏ query parameters nếu có
                            file_name = file_name.split('?')[0]
                    
                    if not file_name.lower().endswith(".pdf"): # Đảm bảo tên file có đuôi .pdf
                        file_name += ".pdf"
                        
                    file_path = os.path.join(download_dir, file_name)

                    # Kiểm tra nếu file đã tồn tại
                    if os.path.exists(file_path):
                        self.log_message(f"Bỏ qua: '{file_name}' đã tồn tại.", "INFO")
                        continue

                    self.log_message(f"Đang tải ({i+1}/{len(pdf_links)}): {file_name} từ {pdf_url}")
                    
                    pdf_response = requests.get(pdf_url, headers=headers, stream=True, timeout=60)
                    pdf_response.raise_for_status()

                    # Ghi file PDF xuống đĩa
                    with open(file_path, 'wb') as f:
                        for chunk in pdf_response.iter_content(chunk_size=8192):
                            f.write(chunk)
                    
                    self.log_message(f"Đã tải xong: {file_name}", "SUCCESS")
                    downloaded_count += 1
                    time.sleep(1) # Thêm một chút độ trễ để tránh làm quá tải server

                except requests.exceptions.RequestException as e:
                    self.log_message(f"Lỗi khi tải {pdf_url}: {e}", "ERROR")
                    failed_count += 1
                except Exception as e:
                    self.log_message(f"Lỗi không xác định khi xử lý {pdf_url}: {e}", "ERROR")
                    failed_count += 1
            
            summary_message = f"Hoàn tất! Đã tải xuống {downloaded_count} bài báo."
            if failed_count > 0:
                summary_message += f" {failed_count} bài báo tải thất bại."
            
            self.log_message(summary_message, "INFO")
            messagebox.showinfo("Hoàn tất", summary_message)

        except requests.exceptions.Timeout:
            self.log_message("Lỗi: Yêu cầu truy cập trang web bị timeout.", "ERROR")
            messagebox.showerror("Lỗi", "Yêu cầu truy cập trang web bị timeout. Vui lòng kiểm tra kết nối mạng hoặc URL.")
        except requests.exceptions.RequestException as e:
            self.log_message(f"Lỗi khi truy cập URL: {e}", "ERROR")
            messagebox.showerror("Lỗi", f"Không thể truy cập URL: {e}")
        except Exception as e:
            self.log_message(f"Đã xảy ra lỗi không mong muốn: {e}", "CRITICAL")
            messagebox.showerror("Lỗi nghiêm trọng", f"Đã xảy ra lỗi không mong muốn: {e}")
        finally:
            # Kích hoạt lại nút tải
            self.download_button.config(state=tk.NORMAL, text="Bắt đầu tải")
            self.status_var.set("Sẵn sàng")


if __name__ == '__main__':
    root = tk.Tk()
    app = PaperDownloaderApp(root)
    root.mainloop()
