import tkinter as tk
from tkinter import filedialog, scrolledtext, messagebox, ttk
import requests
from bs4 import BeautifulSoup
import os
import threading
import time
from urllib.parse import urljoin, urlparse
import re # For year extraction

class PaperDownloaderApp:
    ITEMS_PER_PAGE = 15

    def __init__(self, root):
        self.root = root
        self.root.title("Trình Tải Bài Báo - Tách Lọc & Lấy Chi Tiết")
        self.root.geometry("1150x870") # Tăng chiều cao một chút

        self.url_var = tk.StringVar(value="https.openaccess.thecvf.com/CVPR2024?day=all")
        self.download_dir_var = tk.StringVar(value=os.getcwd())
        self.year_filter_var = tk.StringVar()
        self.keyword_filter_var = tk.StringVar()
        
        self.all_potential_items = [] 
        self.filtered_items_for_display = []
        
        self.current_page = 1
        self.total_pages = 0
        
        self.http_session = requests.Session()
        self.http_session.headers.update({'User-Agent': 'Mozilla/5.0 (compatible; PaperDownloaderApp/1.6)'})

        main_paned_window = ttk.PanedWindow(root, orient=tk.HORIZONTAL)
        main_paned_window.pack(fill=tk.BOTH, expand=True)

        left_frame_outer = ttk.Frame(main_paned_window, padding=10)
        main_paned_window.add(left_frame_outer, weight=3)

        # --- Khung Điều Khiển ---
        controls_main_frame = ttk.LabelFrame(left_frame_outer, text="Điều khiển", padding=10)
        controls_main_frame.pack(fill=tk.X, pady=(0,10))

        # Phần URL và Thư mục
        source_frame = ttk.Frame(controls_main_frame)
        source_frame.pack(fill=tk.X, pady=2)
        ttk.Label(source_frame, text="URL Trang Danh Sách:", width=20, anchor="w").pack(side=tk.LEFT, padx=(0,5))
        self.url_entry = ttk.Entry(source_frame, textvariable=self.url_var)
        self.url_entry.pack(side=tk.LEFT, expand=True, fill=tk.X)

        dir_input_frame = ttk.Frame(controls_main_frame)
        dir_input_frame.pack(fill=tk.X, pady=2)
        ttk.Label(dir_input_frame, text="Thư mục lưu:", width=20, anchor="w").pack(side=tk.LEFT, padx=(0,5))
        self.dir_entry = ttk.Entry(dir_input_frame, textvariable=self.download_dir_var)
        self.dir_entry.pack(side=tk.LEFT, expand=True, fill=tk.X)
        self.browse_button = ttk.Button(dir_input_frame, text="Chọn", command=self.choose_directory, width=8)
        self.browse_button.pack(side=tk.LEFT, padx=(5,0))

        self.search_button = ttk.Button(controls_main_frame, text="1. Tìm Mục từ Trang Danh Sách", command=self.start_initial_fetch_thread, style="Accent.TButton")
        self.search_button.pack(pady=(10,5), fill=tk.X)
        
        # Phần Bộ lọc
        filter_controls_frame = ttk.LabelFrame(controls_main_frame, text="Bộ lọc (Áp dụng cho danh sách hiện có)", padding=5)
        filter_controls_frame.pack(fill=tk.X, pady=(5,5))

        year_filter_frame = ttk.Frame(filter_controls_frame)
        year_filter_frame.pack(fill=tk.X, pady=2)
        ttk.Label(year_filter_frame, text="Lọc theo Năm:", width=20, anchor="w").pack(side=tk.LEFT, padx=(0,5))
        self.year_filter_entry = ttk.Entry(year_filter_frame, textvariable=self.year_filter_var)
        self.year_filter_entry.pack(side=tk.LEFT, expand=True, fill=tk.X)

        keyword_filter_frame = ttk.Frame(filter_controls_frame)
        keyword_filter_frame.pack(fill=tk.X, pady=2)
        ttk.Label(keyword_filter_frame, text="Lọc Từ khóa (Tiêu đề/Tóm tắt nếu có):", width=20, anchor="w").pack(side=tk.LEFT, padx=(0,5))
        self.keyword_filter_entry = ttk.Entry(keyword_filter_frame, textvariable=self.keyword_filter_var)
        self.keyword_filter_entry.pack(side=tk.LEFT, expand=True, fill=tk.X)

        self.apply_filters_only_button = ttk.Button(filter_controls_frame, text="2. Áp dụng Bộ lọc (Không lấy chi tiết)", command=self.apply_filters_only)
        self.apply_filters_only_button.pack(pady=5, fill=tk.X)

        # Nút Lấy Chi Tiết
        self.fetch_details_button = ttk.Button(controls_main_frame, text="3. Lấy Chi Tiết (PDF, Tóm tắt) cho Kết quả Lọc", command=self.start_fetch_details_for_filtered_thread)
        self.fetch_details_button.pack(pady=5, fill=tk.X)
        
        style = ttk.Style()
        style.configure("Accent.TButton", font=('Helvetica', 10, 'bold'))

        # --- Khung Kết quả ---
        results_outer_frame = ttk.LabelFrame(left_frame_outer, text="Các Mục Tìm Thấy", padding=10)
        results_outer_frame.pack(fill=tk.BOTH, expand=True)

        self.results_count_label = ttk.Label(results_outer_frame, text="Tổng số mục: 0 | Phù hợp bộ lọc: 0")
        self.results_count_label.pack(fill=tk.X, pady=(0,5))

        actions_on_selection_frame = ttk.Frame(results_outer_frame, padding=(0,5))
        actions_on_selection_frame.pack(fill=tk.X)
        self.show_abstracts_button = ttk.Button(actions_on_selection_frame, text="Hiển thị Abstract (Mục đã chọn)", command=self.show_selected_abstracts)
        self.show_abstracts_button.pack(side=tk.LEFT, padx=(0,5))
        self.download_selected_items_button_specific = ttk.Button(actions_on_selection_frame, text="Tải PDF (Mục đã chọn)", command=self.start_download_selected_thread)
        self.download_selected_items_button_specific.pack(side=tk.LEFT, padx=5)

        self.results_canvas = tk.Canvas(results_outer_frame, borderwidth=0, highlightthickness=0)
        self.results_frame = ttk.Frame(self.results_canvas)
        self.results_scrollbar = ttk.Scrollbar(results_outer_frame, orient="vertical", command=self.results_canvas.yview)
        self.results_canvas.configure(yscrollcommand=self.results_scrollbar.set)
        self.results_scrollbar.pack(side="right", fill="y")
        self.results_canvas.pack(side="left", fill="both", expand=True)
        self.canvas_window = self.results_canvas.create_window((0, 0), window=self.results_frame, anchor="nw")
        self.results_frame.bind("<Configure>", lambda e: self.results_canvas.configure(scrollregion=self.results_canvas.bbox("all")))
        self.results_canvas.bind('<Configure>', self.on_canvas_configure)

        select_all_frame = ttk.Frame(results_outer_frame)
        select_all_frame.pack(fill=tk.X, pady=(5,0), before=self.results_canvas)
        self.select_all_var = tk.BooleanVar()
        self.select_all_button = ttk.Checkbutton(select_all_frame, text="Chọn/Bỏ chọn tất cả (kết quả đã lọc, có PDF)", variable=self.select_all_var, command=self.toggle_select_all_filtered_and_valid)
        self.select_all_button.pack(side=tk.LEFT, padx=5)

        pagination_frame = ttk.Frame(results_outer_frame)
        pagination_frame.pack(fill=tk.X, pady=(0,5), before=self.results_canvas)
        self.prev_button = ttk.Button(pagination_frame, text="<< Trang trước", command=self.prev_page, state=tk.DISABLED)
        self.prev_button.pack(side=tk.LEFT, padx=5)
        self.page_label = ttk.Label(pagination_frame, text="Trang 0/0")
        self.page_label.pack(side=tk.LEFT, expand=True, fill=tk.X)
        self.next_button = ttk.Button(pagination_frame, text="Trang sau >>", command=self.next_page, state=tk.DISABLED)
        self.next_button.pack(side=tk.RIGHT, padx=5)

        # --- Khung Log (bên phải) ---
        right_frame = ttk.Frame(main_paned_window, padding=10)
        main_paned_window.add(right_frame, weight=2)
        log_frame = ttk.LabelFrame(right_frame, text="Trạng thái và Log", padding=10)
        log_frame.pack(fill=tk.BOTH, expand=True)
        self.log_area = scrolledtext.ScrolledText(log_frame, wrap=tk.WORD, height=15)
        self.log_area.pack(fill=tk.BOTH, expand=True)
        self.log_area.configure(state='disabled')

        # --- Thanh trạng thái và Nút tải chính (dưới cùng) ---
        bottom_frame = ttk.Frame(root, padding=10)
        bottom_frame.pack(fill=tk.X, side=tk.BOTTOM)
        self.main_download_button = ttk.Button(bottom_frame, text="Tải Tất Cả Mục Đã Chọn (có PDF)", command=self.start_download_selected_thread, style="Accent.TButton")
        self.main_download_button.pack(side=tk.LEFT, padx=(0,10), fill=tk.X, expand=True)
        self.status_var = tk.StringVar(value="Sẵn sàng")
        self.status_bar = ttk.Label(bottom_frame, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        self.status_bar.pack(side=tk.LEFT, fill=tk.X, expand=True)

    def on_canvas_configure(self, event):
        self.results_canvas.itemconfig(self.canvas_window, width=event.width)

    def log_message(self, message, level="INFO"):
        self.log_area.configure(state='normal')
        timestamp = time.strftime("%H:%M:%S", time.localtime())
        self.log_area.insert(tk.END, f"[{timestamp} {level}] {message}\n")
        self.log_area.configure(state='disabled')
        self.log_area.see(tk.END)
        if level not in ["DEBUG", "SUCCESS"]: self.status_var.set(message.split('\n')[0])
        self.root.update_idletasks()

    def choose_directory(self):
        directory = filedialog.askdirectory()
        if directory: self.download_dir_var.set(directory)

    def _clear_displayed_items(self):
        for widget in self.results_frame.winfo_children(): widget.destroy()
        self.results_canvas.yview_moveto(0)
        self.results_canvas.configure(scrollregion=self.results_canvas.bbox("all"))

    def _display_page_items(self, items_on_page):
        self._clear_displayed_items()
        if not items_on_page:
            ttk.Label(self.results_frame, text="Không có mục nào để hiển thị trên trang này.").pack(pady=10)
            return

        for item_info in items_on_page:
            item_frame = ttk.Frame(self.results_frame, padding=(0, 2))
            item_frame.pack(fill=tk.X, expand=True)
            
            # Checkbox chỉ enable nếu có pdf_url (sau khi đã fetch details)
            cb_state = tk.NORMAL if item_info.get('pdf_url') else tk.DISABLED
            cb = ttk.Checkbutton(item_frame, variable=item_info['selected_var'], state=cb_state)
            cb.pack(side=tk.LEFT, padx=(0,5))
            
            display_text = item_info.get('title', "Chưa có tiêu đề")
            if display_text == "Chưa có tiêu đề" or not display_text.strip():
                raw_text_main_page = item_info.get('raw_text_main_page', "Không có nội dung thô")
                display_text = raw_text_main_page[:120] + "..." if len(raw_text_main_page) > 120 else raw_text_main_page
            elif len(display_text) > 100: 
                 display_text = display_text[:97] + "..."

            year_info_display = item_info.get('year_info', 'N/A')
            full_display_text = f"{display_text} ({year_info_display})" # Bỏ [PDF] [Abs]
            
            title_label = ttk.Label(item_frame, text=full_display_text, wraplength=self.results_canvas.winfo_width() - 80)
            title_label.pack(side=tk.LEFT, fill=tk.X, expand=True)
            
            tooltip_text_func = lambda i=item_info: (
                f"Tiêu đề: {i.get('title', 'N/A')}\n"
                f"Năm: {i.get('year_info', 'N/A')}\n"
                f"URL Chi tiết: {i.get('details_page_url', 'N/A')}\n"
                f"URL PDF: {i.get('pdf_url', 'Chưa lấy') if not i.get('details_fetched_flag') else (i.get('pdf_url') or 'Không có')}\n"
                f"Tóm tắt: {'Chưa lấy' if not i.get('details_fetched_flag') else ('Có' if i.get('abstract_text') else 'Không có')}\n"
                f"---\n{i.get('abstract_text', '')[:500]}{'...' if i.get('abstract_text') and len(i.get('abstract_text')) > 500 else ''}"
            )
            ToolTip(title_label, text_func=tooltip_text_func)

        self.results_frame.update_idletasks()
        self.results_canvas.config(scrollregion=self.results_canvas.bbox("all"))

    def update_view_and_pagination(self):
        if not self.filtered_items_for_display:
            self.total_pages = 0
            self.current_page = 0
        else:
            self.total_pages = (len(self.filtered_items_for_display) + self.ITEMS_PER_PAGE - 1) // self.ITEMS_PER_PAGE
        
        if self.current_page < 1 and self.total_pages > 0: self.current_page = 1
        if self.current_page > self.total_pages: self.current_page = self.total_pages

        start_index = (self.current_page - 1) * self.ITEMS_PER_PAGE if self.current_page > 0 else 0
        end_index = start_index + self.ITEMS_PER_PAGE
        items_for_current_page = self.filtered_items_for_display[start_index:end_index]
        
        self._display_page_items(items_for_current_page)
        self._update_pagination_controls()
        self._update_results_count_label()

    def _update_pagination_controls(self):
        self.page_label.config(text=f"Trang {self.current_page}/{self.total_pages if self.total_pages > 0 else 0}")
        self.prev_button.config(state=tk.NORMAL if self.current_page > 1 else tk.DISABLED)
        self.next_button.config(state=tk.NORMAL if self.current_page < self.total_pages else tk.DISABLED)

    def _update_results_count_label(self):
        total_all = len(self.all_potential_items)
        total_filtered = len(self.filtered_items_for_display)
        self.results_count_label.config(text=f"Tổng số mục: {total_all} | Phù hợp bộ lọc: {total_filtered}")

    def prev_page(self):
        if self.current_page > 1:
            self.current_page -= 1
            self.update_view_and_pagination()

    def next_page(self):
        if self.current_page < self.total_pages:
            self.current_page += 1
            self.update_view_and_pagination()

    def start_initial_fetch_thread(self):
        url = self.url_var.get()
        if not url or not urlparse(url).scheme or not urlparse(url).netloc:
            messagebox.showerror("Lỗi URL", "Vui lòng nhập URL trang web hợp lệ.")
            return

        self.search_button.config(state=tk.DISABLED, text="Đang tìm từ Trang Danh Sách...")
        self.apply_filters_only_button.config(state=tk.DISABLED)
        self.fetch_details_button.config(state=tk.DISABLED)
        self.log_message("Bắt đầu tìm tất cả mục từ Trang Danh Sách...")
        self._clear_displayed_items()
        self.all_potential_items.clear()
        self.filtered_items_for_display.clear()
        self.current_page = 0 
        self.total_pages = 0
        self.update_view_and_pagination()

        thread = threading.Thread(target=self._fetch_main_list_items, args=(url,))
        thread.daemon = True
        thread.start()

    def _parse_main_list_item(self, dt_tag_str, dd_tag_str, base_url):
        item_data = {'dt_tag_str': dt_tag_str, 'dd_tag_str': dd_tag_str, 
                     'selected_var': tk.BooleanVar(value=False),
                     'details_fetched_flag': False} # Cờ mới
        title = "Chưa có tiêu đề"
        details_page_url = None
        raw_text_main_page = ""
        year_info = "N/A"

        if dt_tag_str:
            dt_soup = BeautifulSoup(dt_tag_str, 'html.parser').dt
            if dt_soup:
                title_anchor = dt_soup.find('a', href=True)
                if title_anchor:
                    title = title_anchor.get_text(strip=True)
                    details_page_url = urljoin(base_url, title_anchor['href'])
                else:
                    title = dt_soup.get_text(strip=True)
                raw_text_main_page += dt_soup.get_text(separator=' ', strip=True)

        if dd_tag_str:
            dd_soup = BeautifulSoup(dd_tag_str, 'html.parser').dd
            if dd_soup:
                raw_text_main_page += " " + dd_soup.get_text(separator=' ', strip=True)
        
        if raw_text_main_page:
            year_match = re.search(r'\b(19\d{2}|20\d{2}|21\d{2})\b', raw_text_main_page)
            if year_match:
                year_info = year_match.group(0)
        
        item_data['title'] = title
        item_data['details_page_url'] = details_page_url
        item_data['raw_text_main_page'] = raw_text_main_page.strip()
        item_data['year_info'] = year_info
        return item_data

    def _fetch_main_list_items(self, page_url):
        try:
            response = self.http_session.get(page_url, timeout=45)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            
            self.all_potential_items = []
            potential_item_count = 0

            dts = soup.find_all('dt', class_='ptitle')
            if dts:
                self.log_message(f"Tìm thấy {len(dts)} thẻ <dt class='ptitle'> trên trang danh sách.")
                for dt_tag in dts:
                    dd_tag = dt_tag.find_next_sibling('dd')
                    if dd_tag:
                        potential_item_count +=1
                        parsed_item = self._parse_main_list_item(str(dt_tag), str(dd_tag), page_url)
                        self.all_potential_items.append(parsed_item)
            else:
                self.log_message("Không tìm thấy thẻ <dt class='ptitle'> nào. Kiểm tra lại cấu trúc trang.", "WARNING")

            self.log_message(f"Đã phân tích trang danh sách. {potential_item_count} mục được xử lý.")
            self.log_message(f"Số mục đã lưu vào all_potential_items: {len(self.all_potential_items)}.")
            
            self.filtered_items_for_display = list(self.all_potential_items)
            self.current_page = 1
            self.update_view_and_pagination()

        except requests.exceptions.Timeout:
            self.log_message("Lỗi: Timeout khi truy cập trang danh sách.", "ERROR")
        except requests.exceptions.RequestException as e:
            self.log_message(f"Lỗi khi truy cập trang danh sách: {e}", "ERROR")
        except Exception as e:
            self.log_message(f"Lỗi không mong muốn khi phân tích trang danh sách: {e}", "CRITICAL")
        finally:
            self.search_button.config(state=tk.NORMAL, text="1. Tìm Mục từ Trang Danh Sách")
            self.apply_filters_only_button.config(state=tk.NORMAL)
            self.fetch_details_button.config(state=tk.NORMAL)
            self.status_var.set(f"Tìm thấy {len(self.all_potential_items)} mục. Áp dụng bộ lọc hoặc lấy chi tiết.")

    def apply_filters_only(self):
        if not self.all_potential_items:
            messagebox.showinfo("Chưa có dữ liệu", "Vui lòng 'Tìm Mục từ Trang Danh Sách' trước.")
            return

        self.log_message("Chỉ áp dụng bộ lọc (không lấy chi tiết)...")
        year_filter = self.year_filter_var.get().strip()
        keyword_filter = self.keyword_filter_var.get().strip().lower()

        self.filtered_items_for_display = []
        for item_data in self.all_potential_items:
            year_match = True
            if year_filter:
                year_match = (year_filter in item_data.get('year_info', ''))
            
            keyword_match = True
            if keyword_filter:
                # Tìm từ khóa trong tiêu đề, raw_text_main_page, và abstract (nếu đã có)
                text_to_search = (item_data.get('title', '') + " " + 
                                  item_data.get('raw_text_main_page', '') + " " +
                                  item_data.get('abstract_text', '')).lower()
                keyword_match = (keyword_filter in text_to_search)
            
            if year_match and keyword_match:
                self.filtered_items_for_display.append(item_data)
        
        self.log_message(f"Đã lọc, còn lại {len(self.filtered_items_for_display)} mục.")
        self.current_page = 1
        self.update_view_and_pagination()
        self.status_var.set(f"Đã áp dụng bộ lọc. {len(self.filtered_items_for_display)} mục phù hợp. Nhấn 'Lấy Chi Tiết' nếu cần.")
        self.select_all_var.set(False)


    def _fetch_and_parse_details_page(self, item_data, base_list_page_url):
        if not item_data.get('details_page_url'): return item_data
        if item_data.get('details_fetched_flag'): return item_data

        details_url = item_data['details_page_url']
        try:
            response = self.http_session.get(details_url, timeout=30)
            response.raise_for_status()
            details_soup = BeautifulSoup(response.content, 'html.parser')

            abstract_div = details_soup.find('div', id='abstract')
            item_data['abstract_text'] = abstract_div.get_text(separator=' ', strip=True) if abstract_div else None

            pdf_url_on_details_page = None
            content_div = details_soup.find('div', id='content') # Thường chứa link PDF trên trang chi tiết CVF
            scope_for_pdf_link = content_div if content_div else details_soup

            if scope_for_pdf_link:
                for a_tag in scope_for_pdf_link.find_all('a', href=True):
                    tag_text = a_tag.get_text(strip=True).lower()
                    if tag_text == '[pdf]':
                        pdf_url_on_details_page = urljoin(details_url, a_tag['href'])
                        break
                if not pdf_url_on_details_page: 
                    generic_pdf_anchor = scope_for_pdf_link.find('a', href=lambda h: h and str(h).lower().endswith('.pdf'))
                    if generic_pdf_anchor:
                         generic_text = generic_pdf_anchor.get_text(strip=True).lower()
                         if generic_text not in ['[supp]', '[supplementary]', '[bib]', '[bibtex]', '[slides]', '[video]']:
                            pdf_url_on_details_page = urljoin(details_url, generic_pdf_anchor['href'])
            item_data['pdf_url'] = pdf_url_on_details_page
            item_data['details_fetched_flag'] = True
        except Exception as e: # Bắt lỗi chung cho request và parse
            self.log_message(f"Lỗi khi xử lý chi tiết {details_url}: {str(e)[:100]}", "ERROR")
            item_data['details_fetched_flag'] = True # Đánh dấu đã thử fetch để không thử lại liên tục
            item_data['pdf_url'] = None
            item_data['abstract_text'] = "Lỗi khi lấy chi tiết."
        time.sleep(0.05)
        return item_data

    def _thread_fetch_details_for_list(self, list_to_fetch_details_for, page_url_for_joins):
        """Luồng xử lý việc lấy chi tiết cho một danh sách các mục."""
        total_items = len(list_to_fetch_details_for)
        for i, item_data_ref in enumerate(list_to_fetch_details_for): # item_data_ref là tham chiếu đến mục trong filtered_items_for_display
            if i % 5 == 0 or i == total_items - 1:
                self.status_var.set(f"Đang lấy chi tiết: {i+1}/{total_items}...")
                self.root.update_idletasks()
            
            # Gọi _fetch_and_parse_details_page, nó sẽ cập nhật item_data_ref tại chỗ
            # vì item_data_ref là một dictionary (mutable)
            self._fetch_and_parse_details_page(item_data_ref, page_url_for_joins)
        
        self.log_message(f"Hoàn tất lấy chi tiết cho {total_items} mục.")
        self.update_view_and_pagination() # Cập nhật lại view để hiển thị checkbox đúng
        self.status_var.set(f"Đã lấy chi tiết. {len(self.filtered_items_for_display)} mục trong danh sách hiện tại.")
        self.fetch_details_button.config(state=tk.NORMAL, text="3. Lấy Chi Tiết (PDF, Tóm tắt) cho Kết quả Lọc")


    def start_fetch_details_for_filtered_thread(self):
        if not self.filtered_items_for_display:
            messagebox.showinfo("Danh sách rỗng", "Không có mục nào trong danh sách kết quả lọc để lấy chi tiết.")
            return

        # Kiểm tra xem có mục nào chưa được fetch chi tiết không
        items_needing_details = [item for item in self.filtered_items_for_display if not item.get('details_fetched_flag')]
        if not items_needing_details:
            messagebox.showinfo("Đã lấy chi tiết", "Tất cả các mục trong danh sách hiện tại đã được lấy thông tin chi tiết.")
            self.update_view_and_pagination() # Vẫn cập nhật view phòng trường hợp
            return

        self.log_message(f"Bắt đầu lấy chi tiết cho {len(items_needing_details)} mục trong kết quả lọc...")
        self.fetch_details_button.config(state=tk.DISABLED, text="Đang lấy chi tiết...")
        
        # Chúng ta sẽ truyền danh sách items_needing_details vào luồng
        # Hàm _fetch_and_parse_details_page sẽ cập nhật trực tiếp các dict này
        thread = threading.Thread(target=self._thread_fetch_details_for_list, 
                                  args=(items_needing_details, self.url_var.get()))
        thread.daemon = True
        thread.start()


    def show_selected_abstracts(self):
        selected_items_with_abstract = [
            item for item in self.filtered_items_for_display 
            if item['selected_var'].get() and item.get('abstract_text')
        ]
        if not selected_items_with_abstract:
            messagebox.showinfo("Không có tóm tắt", "Không có mục nào được chọn, hoặc các mục đã chọn chưa có tóm tắt (cần 'Lấy Chi Tiết' trước).")
            return

        abstract_window = tk.Toplevel(self.root)
        abstract_window.title("Tóm tắt các Bài báo Đã chọn")
        abstract_window.geometry("800x600")
        text_area = scrolledtext.ScrolledText(abstract_window, wrap=tk.WORD, padx=5, pady=5, font=("Arial", 10))
        text_area.pack(expand=True, fill=tk.BOTH)
        text_area.configure(state='disabled')
        full_abstract_content = ""
        for item in selected_items_with_abstract:
            full_abstract_content += f"TIÊU ĐỀ: {item.get('title', 'N/A')}\n"
            full_abstract_content += f"TÓM TẮT:\n{item.get('abstract_text', 'Không có tóm tắt.')}\n"
            full_abstract_content += "--------------------------------------------------\n\n"
        text_area.configure(state='normal')
        text_area.delete(1.0, tk.END)
        text_area.insert(tk.END, full_abstract_content)
        text_area.configure(state='disabled')
        abstract_window.transient(self.root)
        abstract_window.grab_set()
        self.root.wait_window(abstract_window)

    def toggle_select_all_filtered_and_valid(self):
        is_selected = self.select_all_var.get()
        for item_info in self.filtered_items_for_display:
            if item_info.get('pdf_url'): # Chỉ cho phép chọn nếu có pdf_url
                item_info['selected_var'].set(is_selected)
        self.update_view_and_pagination() # Cập nhật lại hiển thị để thấy thay đổi

    def start_download_selected_thread(self):
        selected_to_download = [p for p in self.filtered_items_for_display if p['selected_var'].get() and p.get('pdf_url')]
        if not selected_to_download:
            messagebox.showinfo("Chưa chọn hoặc không có PDF", "Vui lòng chọn ít nhất một mục có liên kết PDF để tải (cần 'Lấy Chi Tiết' trước).")
            return
        download_dir = self.download_dir_var.get()
        if not download_dir or not os.path.isdir(download_dir):
            messagebox.showerror("Lỗi Thư mục", "Vui lòng chọn một thư mục lưu hợp lệ.")
            return
        
        self.main_download_button.config(state=tk.DISABLED, text="Đang tải...")
        self.download_selected_items_button_specific.config(state=tk.DISABLED, text="Đang tải...")
        self.log_message(f"Bắt đầu tải {len(selected_to_download)} mục đã chọn...")
        thread = threading.Thread(target=self._download_selected_items_logic, args=(selected_to_download, download_dir))
        thread.daemon = True
        thread.start()

    def _download_single_pdf(self, pdf_url, file_path, item_title):
        try:
            self.log_message(f"Đang tải: {item_title[:70]}...", "DEBUG")
            pdf_response = self.http_session.get(pdf_url, stream=True, timeout=120)
            pdf_response.raise_for_status()
            with open(file_path, 'wb') as f:
                for chunk in pdf_response.iter_content(chunk_size=8192): f.write(chunk)
            self.log_message(f"Đã tải: {os.path.basename(file_path)}", "SUCCESS")
            return True
        except requests.exceptions.Timeout: self.log_message(f"Lỗi Timeout: {item_title[:70]}...", "ERROR")
        except requests.exceptions.RequestException as e: self.log_message(f"Lỗi tải {item_title[:70]}...: {e}", "ERROR")
        except Exception as e: self.log_message(f"Lỗi không rõ khi tải {item_title[:70]}...: {e}", "ERROR")
        return False

    def _download_selected_items_logic(self, items_to_download, download_dir):
        downloaded_count, failed_count = 0, 0
        for item_info in items_to_download:
            title_for_filename = item_info.get('title', "Unknown_Paper")
            if title_for_filename == "Unknown_Paper" or not title_for_filename.strip() or title_for_filename == "Chưa có tiêu đề":
                 title_for_filename = item_info.get('raw_text_main_page', 'Downloaded_Item')[:60]

            base_name = "".join(c if c.isalnum() or c in (' ','.','_','-') else '_' for c in title_for_filename)
            base_name = base_name.strip().replace(' ', '_')
            base_name = re.sub(r'__+', '_', base_name) 
            base_name = base_name[:100] 
            
            file_name = base_name + ".pdf"
            if len(base_name.replace("_","").strip()) < 5:
                url_fn = os.path.basename(urlparse(item_info['pdf_url']).path)
                if url_fn and url_fn.lower().endswith(".pdf"): file_name = url_fn
                else: file_name = f"paper_{int(time.time())}_{downloaded_count}.pdf"
            
            file_path = os.path.join(download_dir, file_name)
            if os.path.exists(file_path):
                self.log_message(f"Bỏ qua (đã tồn tại): {file_name}", "INFO")
                continue
            
            if self._download_single_pdf(item_info['pdf_url'], file_path, title_for_filename):
                downloaded_count += 1
            else:
                failed_count += 1
            time.sleep(0.05)

        summary = f"Hoàn tất! Đã tải {downloaded_count} mục."
        if failed_count > 0: summary += f" Thất bại {failed_count} mục."
        self.log_message(summary, "INFO")
        if failed_count > 0: messagebox.showwarning("Hoàn tất với lỗi", summary)
        else: messagebox.showinfo("Hoàn tất", summary)
        
        self.main_download_button.config(state=tk.NORMAL, text="Tải Tất Cả Mục Đã Chọn (có PDF)")
        self.download_selected_items_button_specific.config(state=tk.NORMAL, text="Tải PDF (Mục đã chọn)")
        self.status_var.set("Sẵn sàng")

class ToolTip:
    def __init__(self, widget, text_func):
        self.widget = widget
        self.text_func = text_func
        self.tooltip_window = None
        self.show_id = None 
        self.hide_id = None 
        widget.bind("<Enter>", self.schedule_show_tooltip)
        widget.bind("<Leave>", self.schedule_hide_tooltip)
        widget.bind("<Button-1>", lambda e: self.hide_tooltip_now())

    def schedule_show_tooltip(self, event):
        self.cancel_hide() 
        if self.tooltip_window: return 
        self.show_id = self.widget.after(700, lambda: self.show_tooltip_now(event))

    def show_tooltip_now(self, event):
        if self.tooltip_window: self.tooltip_window.destroy() 
        try: text = self.text_func()
        except Exception: return
        if not text: return
        x, y = event.x_root + 20, event.y_root + 15
        self.tooltip_window = tk.Toplevel(self.widget)
        self.tooltip_window.wm_overrideredirect(True)
        self.tooltip_window.wm_attributes("-topmost", True)
        label = ttk.Label(self.tooltip_window, text=text, justify='left',
                          background="#FFFFE0", relief="solid", borderwidth=1, wraplength=600, padding=5)
        label.pack(ipadx=1)
        self.tooltip_window.update_idletasks()
        tip_width, tip_height = self.tooltip_window.winfo_width(), self.tooltip_window.winfo_height()
        screen_width, screen_height = self.widget.winfo_screenwidth(), self.widget.winfo_screenheight()
        if x + tip_width > screen_width: x = screen_width - tip_width - 10
        if y + tip_height > screen_height: y = event.y_root - tip_height - 10 
        if x < 0: x = 10
        if y < 0: y = 10
        self.tooltip_window.wm_geometry(f"+{int(x)}+{int(y)}")
        self.tooltip_window.bind("<Leave>", lambda e: self.hide_tooltip_now())
        label.bind("<Leave>", lambda e: self.hide_tooltip_now())

    def schedule_hide_tooltip(self, event=None):
        self.cancel_show() 
        if self.tooltip_window:
             self.hide_id = self.widget.after(150, self.check_mouse_and_hide)

    def check_mouse_and_hide(self):
        if self.tooltip_window:
            try:
                widget_x, widget_y = self.widget.winfo_rootx(), self.widget.winfo_rooty()
                widget_w, widget_h = self.widget.winfo_width(), self.widget.winfo_height()
                tip_x, tip_y = self.tooltip_window.winfo_rootx(), self.tooltip_window.winfo_rooty()
                tip_w, tip_h = self.tooltip_window.winfo_width(), self.tooltip_window.winfo_height()
                mouse_x, mouse_y = self.widget.winfo_pointerxy()
                on_widget = (widget_x <= mouse_x < widget_x + widget_w and
                             widget_y <= mouse_y < widget_y + widget_h)
                on_tooltip = (tip_x <= mouse_x < tip_x + tip_w and
                              tip_y <= mouse_y < tip_y + tip_h)
                if not on_widget and not on_tooltip: self.hide_tooltip_now()
                else: self.hide_id = self.widget.after(150, self.check_mouse_and_hide)
            except tk.TclError: 
                self.hide_tooltip_now()

    def hide_tooltip_now(self, event=None):
        self.cancel_show()
        self.cancel_hide()
        if self.tooltip_window:
            try: self.tooltip_window.destroy()
            except tk.TclError: pass 
        self.tooltip_window = None

    def cancel_show(self):
        if self.show_id:
            try: self.widget.after_cancel(self.show_id)
            except tk.TclError: pass
            self.show_id = None
            
    def cancel_hide(self):
        if self.hide_id:
            try: self.widget.after_cancel(self.hide_id)
            except tk.TclError: pass
            self.hide_id = None

if __name__ == '__main__':
    root = tk.Tk()
    try:
        style = ttk.Style(root)
        available_themes = style.theme_names() 
        preferred_themes = ['vista', 'xpnative', 'clam',  'alt', 'default'] 
        for theme in preferred_themes:
            if theme in available_themes:
                try: style.theme_use(theme)
                except tk.TclError: pass
                else: break 
    except Exception: pass
    app = PaperDownloaderApp(root)
    root.mainloop()
