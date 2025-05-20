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

    def __init__(self, root_window):
        self.root = root_window
        self.root.title("Paper Downloader - Advanced")
        self.root.geometry("1200x900") # Adjusted size

        # --- Variables ---
        self.list_page_url_var = tk.StringVar(value="https.openaccess.thecvf.com/CVPR2024?day=all")
        self.download_dir_var = tk.StringVar(value=os.getcwd())
        self.year_filter_var = tk.StringVar()
        self.keyword_filter_var = tk.StringVar()
        
        self.all_items_master_list = [] 
        self.items_for_display_list = [] 
        
        self.current_page_num = 1
        self.total_pages_count = 0
        
        self.http_session = requests.Session()
        self.http_session.headers.update({'User-Agent': 'Mozilla/5.0 (compatible; PaperDownloaderApp/1.7)'})

        # --- Main Layout Panes ---
        main_paned_window = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        main_paned_window.pack(fill=tk.BOTH, expand=True)

        # --- Left Pane (Controls & Results) ---
        left_pane_outer_frame = ttk.Frame(main_paned_window, padding=10)
        main_paned_window.add(left_pane_outer_frame, weight=3)

        # --- Control Section ---
        controls_main_frame = ttk.LabelFrame(left_pane_outer_frame, text="Controls", padding=10)
        controls_main_frame.pack(fill=tk.X, pady=(0,10))

        # URL and Directory Input
        source_url_frame = ttk.Frame(controls_main_frame)
        source_url_frame.pack(fill=tk.X, pady=2)
        ttk.Label(source_url_frame, text="List Page URL:", width=20, anchor="w").pack(side=tk.LEFT, padx=(0,5))
        self.url_entry = ttk.Entry(source_url_frame, textvariable=self.list_page_url_var)
        self.url_entry.pack(side=tk.LEFT, expand=True, fill=tk.X)

        download_dir_frame = ttk.Frame(controls_main_frame)
        download_dir_frame.pack(fill=tk.X, pady=2)
        ttk.Label(download_dir_frame, text="Download Directory:", width=20, anchor="w").pack(side=tk.LEFT, padx=(0,5))
        self.dir_entry = ttk.Entry(download_dir_frame, textvariable=self.download_dir_var)
        self.dir_entry.pack(side=tk.LEFT, expand=True, fill=tk.X)
        self.browse_button = ttk.Button(download_dir_frame, text="Browse", command=self.choose_directory, width=8)
        self.browse_button.pack(side=tk.LEFT, padx=(5,0))

        # Step 1 Button: Find Items
        self.find_items_button = ttk.Button(controls_main_frame, text="Find Items from List Page", command=self.start_initial_fetch_thread, style="Accent.TButton")
        self.find_items_button.pack(pady=(10,5), fill=tk.X)
        
        # Step 2 Button: Fetch Details for Selected
        self.fetch_details_for_selected_button = ttk.Button(controls_main_frame, text="Fetch Details for SELECTED Items", command=self.start_fetch_details_for_selected_thread)
        self.fetch_details_for_selected_button.pack(pady=5, fill=tk.X)

        # Filter Section
        filter_controls_frame = ttk.LabelFrame(controls_main_frame, text="Filter Options (Applied to current list)", padding=5)
        filter_controls_frame.pack(fill=tk.X, pady=(5,5))

        year_filter_input_frame = ttk.Frame(filter_controls_frame)
        year_filter_input_frame.pack(fill=tk.X, pady=2)
        ttk.Label(year_filter_input_frame, text="Filter by Year:", width=20, anchor="w").pack(side=tk.LEFT, padx=(0,5))
        self.year_filter_entry = ttk.Entry(year_filter_input_frame, textvariable=self.year_filter_var)
        self.year_filter_entry.pack(side=tk.LEFT, expand=True, fill=tk.X)

        keyword_filter_input_frame = ttk.Frame(filter_controls_frame)
        keyword_filter_input_frame.pack(fill=tk.X, pady=2)
        ttk.Label(keyword_filter_input_frame, text="Filter by Keyword (Title/Abstract if fetched):", width=20, anchor="w").pack(side=tk.LEFT, padx=(0,5))
        self.keyword_filter_entry = ttk.Entry(keyword_filter_input_frame, textvariable=self.keyword_filter_var)
        self.keyword_filter_entry.pack(side=tk.LEFT, expand=True, fill=tk.X)

        # Step 3 Button: Apply Filter
        self.apply_filters_button = ttk.Button(filter_controls_frame, text="Apply Filter (No new detail fetching)", command=self.apply_filters_only)
        self.apply_filters_button.pack(pady=5, fill=tk.X)
        
        style = ttk.Style()
        style.configure("Accent.TButton", font=('Helvetica', 10, 'bold'))

        # --- Results Section ---
        results_display_frame = ttk.LabelFrame(left_pane_outer_frame, text="Found Items", padding=10)
        results_display_frame.pack(fill=tk.BOTH, expand=True)

        self.results_count_label = ttk.Label(results_display_frame, text="Total items: 0 | Matching filter: 0")
        self.results_count_label.pack(fill=tk.X, pady=(0,5))

        # Actions for selected items in the filtered list
        actions_on_selection_bar = ttk.Frame(results_display_frame, padding=(0,5))
        actions_on_selection_bar.pack(fill=tk.X)
        self.show_abstracts_button = ttk.Button(actions_on_selection_bar, text="Show Abstracts (Selected)", command=self.show_selected_abstracts)
        self.show_abstracts_button.pack(side=tk.LEFT, padx=(0,5))
        self.download_selected_action_button = ttk.Button(actions_on_selection_bar, text="Download PDFs (Selected)", command=self.start_download_selected_thread)
        self.download_selected_action_button.pack(side=tk.LEFT, padx=5)

        # Canvas for scrollable results
        self.results_list_canvas = tk.Canvas(results_display_frame, borderwidth=0, highlightthickness=0)
        self.results_items_frame = ttk.Frame(self.results_list_canvas) # Frame inside canvas
        self.results_list_scrollbar = ttk.Scrollbar(results_display_frame, orient="vertical", command=self.results_list_canvas.yview)
        self.results_list_canvas.configure(yscrollcommand=self.results_list_scrollbar.set)
        self.results_list_scrollbar.pack(side="right", fill="y")
        self.results_list_canvas.pack(side="left", fill="both", expand=True)
        self.canvas_window_id = self.results_list_canvas.create_window((0, 0), window=self.results_items_frame, anchor="nw")
        self.results_items_frame.bind("<Configure>", lambda e: self.results_list_canvas.configure(scrollregion=self.results_list_canvas.bbox("all")))
        self.results_list_canvas.bind('<Configure>', self.on_canvas_resize)

        # Select/Deselect All (for currently displayed items)
        select_all_bar = ttk.Frame(results_display_frame)
        select_all_bar.pack(fill=tk.X, pady=(5,0), before=self.results_list_canvas)
        self.select_all_var = tk.BooleanVar()
        self.select_all_checkbox = ttk.Checkbutton(select_all_bar, text="Select/Deselect All Visible", variable=self.select_all_var, command=self.toggle_select_all_visible)
        self.select_all_checkbox.pack(side=tk.LEFT, padx=5)

        # Pagination Controls
        pagination_controls_bar = ttk.Frame(results_display_frame)
        pagination_controls_bar.pack(fill=tk.X, pady=(0,5), before=self.results_list_canvas)
        self.prev_page_button = ttk.Button(pagination_controls_bar, text="<< Previous Page", command=self.go_to_prev_page, state=tk.DISABLED)
        self.prev_page_button.pack(side=tk.LEFT, padx=5)
        self.page_info_label = ttk.Label(pagination_controls_bar, text="Page 0/0")
        self.page_info_label.pack(side=tk.LEFT, expand=True, fill=tk.X)
        self.next_page_button = ttk.Button(pagination_controls_bar, text="Next Page >>", command=self.go_to_next_page, state=tk.DISABLED)
        self.next_page_button.pack(side=tk.RIGHT, padx=5)

        # --- Right Pane (Log) ---
        right_pane_frame = ttk.Frame(main_paned_window, padding=10)
        main_paned_window.add(right_pane_frame, weight=2)
        log_display_frame = ttk.LabelFrame(right_pane_frame, text="Status and Log", padding=10)
        log_display_frame.pack(fill=tk.BOTH, expand=True)
        self.log_text_area = scrolledtext.ScrolledText(log_display_frame, wrap=tk.WORD, height=15, font=("Arial", 9))
        self.log_text_area.pack(fill=tk.BOTH, expand=True)
        self.log_text_area.configure(state='disabled')

        # --- Bottom Bar (Main Download Button & Status) ---
        bottom_bar_frame = ttk.Frame(self.root, padding=10)
        bottom_bar_frame.pack(fill=tk.X, side=tk.BOTTOM)
        self.main_download_all_selected_button = ttk.Button(bottom_bar_frame, text="Download All Selected Items (with PDF)", command=self.start_download_selected_thread, style="Accent.TButton")
        self.main_download_all_selected_button.pack(side=tk.LEFT, padx=(0,10), fill=tk.X, expand=True)
        self.status_message_var = tk.StringVar(value="Ready")
        self.status_bar_label = ttk.Label(bottom_bar_frame, textvariable=self.status_message_var, relief=tk.SUNKEN, anchor=tk.W)
        self.status_bar_label.pack(side=tk.LEFT, fill=tk.X, expand=True)

    def on_canvas_resize(self, event):
        self.results_list_canvas.itemconfig(self.canvas_window_id, width=event.width)

    def log_message(self, message, level="INFO"):
        self.log_text_area.configure(state='normal')
        timestamp = time.strftime("%H:%M:%S", time.localtime())
        self.log_text_area.insert(tk.END, f"[{timestamp} {level}] {message}\n")
        self.log_text_area.configure(state='disabled')
        self.log_text_area.see(tk.END)
        if level not in ["DEBUG", "SUCCESS"]: self.status_message_var.set(message.split('\n')[0])
        self.root.update_idletasks()

    def choose_directory(self):
        directory = filedialog.askdirectory()
        if directory: self.download_dir_var.set(directory)

    def _clear_displayed_items_in_list(self):
        for widget in self.results_items_frame.winfo_children(): widget.destroy()
        self.results_list_canvas.yview_moveto(0)
        self.results_list_canvas.configure(scrollregion=self.results_list_canvas.bbox("all"))

    def _display_page_items_in_list(self, items_on_page):
        self._clear_displayed_items_in_list()
        if not items_on_page:
            ttk.Label(self.results_items_frame, text="No items to display on this page.").pack(pady=10)
            return

        for item_data in items_on_page:
            item_display_frame = ttk.Frame(self.results_items_frame, padding=(0, 2))
            item_display_frame.pack(fill=tk.X, expand=True)
            
            cb = ttk.Checkbutton(item_display_frame, variable=item_data['selected_var'], state=tk.NORMAL)
            cb.pack(side=tk.LEFT, padx=(0,5))
            
            display_title = item_data.get('title', "No Title")
            if display_title == "No Title" or not display_title.strip():
                raw_text = item_data.get('raw_text_main_page', "No raw content")
                display_title = raw_text[:120] + "..." if len(raw_text) > 120 else raw_text
            elif len(display_title) > 100: 
                 display_title = display_title[:97] + "..."

            year_info = item_data.get('year_info', 'N/A')
            full_display_text = f"{display_title} ({year_info})"
            
            title_display_label = ttk.Label(item_display_frame, text=full_display_text, wraplength=self.results_list_canvas.winfo_width() - 80)
            title_display_label.pack(side=tk.LEFT, fill=tk.X, expand=True)
            
            # Corrected instantiation of ToolTip
            tooltip_text_generator = lambda i=item_data: (
                f"Title: {i.get('title', 'N/A')}\n"
                f"Year: {i.get('year_info', 'N/A')}\n"
                f"Details URL: {i.get('details_page_url', 'N/A')}\n"
                f"PDF URL: {'Not fetched yet' if not i.get('details_fetched_flag') else (i.get('pdf_url') or 'Not found')}\n"
                f"Abstract: {'Not fetched yet' if not i.get('details_fetched_flag') else ('Available' if i.get('abstract_text') else 'Not found or N/A')}\n"
                f"---\n{i.get('abstract_text', '')[:500]}{'...' if i.get('abstract_text') and len(i.get('abstract_text')) > 500 else ''}"
            )
            ToolTip(title_display_label, text_func=tooltip_text_generator) # Use text_func

        self.results_items_frame.update_idletasks()
        self.results_list_canvas.config(scrollregion=self.results_list_canvas.bbox("all"))

    def refresh_display_and_pagination(self):
        if not self.items_for_display_list:
            self.total_pages_count = 0
            self.current_page_num = 0
        else:
            self.total_pages_count = (len(self.items_for_display_list) + self.ITEMS_PER_PAGE - 1) // self.ITEMS_PER_PAGE
        
        if self.current_page_num < 1 and self.total_pages_count > 0: self.current_page_num = 1
        if self.current_page_num > self.total_pages_count: self.current_page_num = self.total_pages_count

        start_idx = (self.current_page_num - 1) * self.ITEMS_PER_PAGE if self.current_page_num > 0 else 0
        end_idx = start_idx + self.ITEMS_PER_PAGE
        current_page_items = self.items_for_display_list[start_idx:end_idx]
        
        self._display_page_items_in_list(current_page_items)
        self._update_pagination_ui_controls()
        self._update_results_count_ui_label()

    def _update_pagination_ui_controls(self):
        self.page_info_label.config(text=f"Page {self.current_page_num}/{self.total_pages_count if self.total_pages_count > 0 else 0}")
        self.prev_page_button.config(state=tk.NORMAL if self.current_page_num > 1 else tk.DISABLED)
        self.next_page_button.config(state=tk.NORMAL if self.current_page_num < self.total_pages_count else tk.DISABLED)

    def _update_results_count_ui_label(self):
        total_all = len(self.all_items_master_list)
        total_filtered = len(self.items_for_display_list)
        self.results_count_label.config(text=f"Total items found: {total_all} | Currently displaying: {total_filtered}")

    def go_to_prev_page(self):
        if self.current_page_num > 1:
            self.current_page_num -= 1
            self.refresh_display_and_pagination()

    def go_to_next_page(self):
        if self.current_page_num < self.total_pages_count:
            self.current_page_num += 1
            self.refresh_display_and_pagination()

    def start_initial_fetch_thread(self):
        url = self.list_page_url_var.get()
        if not url or not urlparse(url).scheme or not urlparse(url).netloc:
            messagebox.showerror("URL Error", "Please enter a valid web page URL.")
            return

        self.find_items_button.config(state=tk.DISABLED, text="Finding Items...")
        self.fetch_details_for_selected_button.config(state=tk.DISABLED)
        self.apply_filters_button.config(state=tk.DISABLED)
        self.log_message("Starting to find all items from the list page...")
        self._clear_displayed_items_in_list()
        self.all_items_master_list.clear()
        self.items_for_display_list.clear()
        self.current_page_num = 0 
        self.total_pages_count = 0
        self.refresh_display_and_pagination()

        thread = threading.Thread(target=self._fetch_main_list_items_logic, args=(url,))
        thread.daemon = True
        thread.start()

    def _parse_main_list_item_data(self, dt_tag_str, dd_tag_str, base_url):
        item_data = {'dt_tag_str': dt_tag_str, 'dd_tag_str': dd_tag_str, 
                     'selected_var': tk.BooleanVar(value=False),
                     'details_fetched_flag': False} 
        title = "No Title"
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

    def _fetch_main_list_items_logic(self, page_url):
        try:
            response = self.http_session.get(page_url, timeout=45)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            
            self.all_items_master_list = []
            items_processed_count = 0

            dt_elements = soup.find_all('dt', class_='ptitle')
            if dt_elements:
                self.log_message(f"Found {len(dt_elements)} <dt class='ptitle'> tags on the list page.")
                for dt_tag_element in dt_elements:
                    dd_tag_element = dt_tag_element.find_next_sibling('dd')
                    if dd_tag_element:
                        items_processed_count +=1
                        parsed_item = self._parse_main_list_item_data(str(dt_tag_element), str(dd_tag_element), page_url)
                        self.all_items_master_list.append(parsed_item)
            else:
                self.log_message("No <dt class='ptitle'> tags found. Please check the page structure.", "WARNING")

            self.log_message(f"Finished parsing list page. {items_processed_count} items processed.")
            self.log_message(f"Total items stored in master list: {len(self.all_items_master_list)}.")
            
            self.items_for_display_list = list(self.all_items_master_list)
            self.current_page_num = 1
            self.refresh_display_and_pagination()

        except requests.exceptions.Timeout:
            self.log_message("Error: Timeout while accessing the list page.", "ERROR")
        except requests.exceptions.RequestException as e:
            self.log_message(f"Error accessing list page: {e}", "ERROR")
        except Exception as e:
            self.log_message(f"Unexpected error parsing list page: {e}", "CRITICAL")
            # import traceback # Uncomment for detailed traceback
            # self.log_message(traceback.format_exc(), "DEBUG") # Uncomment for detailed traceback
        finally:
            self.find_items_button.config(state=tk.NORMAL, text="Find Items from List Page")
            self.fetch_details_for_selected_button.config(state=tk.NORMAL)
            self.apply_filters_button.config(state=tk.NORMAL)
            self.status_message_var.set(f"Found {len(self.all_items_master_list)} items. Select items to fetch details or apply filters.")

    def apply_filters_only(self):
        if not self.all_items_master_list:
            messagebox.showinfo("No Data", "Please 'Find Items from List Page' first.")
            return

        self.log_message("Applying filters (details not fetched by this action)...")
        year_val = self.year_filter_var.get().strip()
        keyword_val = self.keyword_filter_var.get().strip().lower()

        self.items_for_display_list = []
        for item_data_dict in self.all_items_master_list:
            year_match_flag = True
            if year_val:
                year_match_flag = (year_val in item_data_dict.get('year_info', ''))
            
            keyword_match_flag = True
            if keyword_val:
                text_to_search = (item_data_dict.get('title', '') + " " + 
                                  item_data_dict.get('raw_text_main_page', '') + " " +
                                  item_data_dict.get('abstract_text', '')).lower() 
                keyword_match_flag = (keyword_val in text_to_search)
            
            if year_match_flag and keyword_match_flag:
                self.items_for_display_list.append(item_data_dict)
        
        self.log_message(f"Filtering complete. {len(self.items_for_display_list)} items match criteria.")
        self.current_page_num = 1
        self.refresh_display_and_pagination()
        self.status_message_var.set(f"Filter applied. {len(self.items_for_display_list)} items match. Select items or fetch details.")
        self.select_all_var.set(False) 

    def _fetch_and_parse_item_details_page(self, item_data_dict, base_list_page_url):
        if not item_data_dict.get('details_page_url'): return
        if item_data_dict.get('details_fetched_flag'): return 

        details_page_actual_url = item_data_dict['details_page_url']
        try:
            response = self.http_session.get(details_page_actual_url, timeout=30)
            response.raise_for_status()
            details_page_soup = BeautifulSoup(response.content, 'html.parser')

            abstract_div_element = details_page_soup.find('div', id='abstract')
            item_data_dict['abstract_text'] = abstract_div_element.get_text(separator=' ', strip=True) if abstract_div_element else None

            pdf_link_on_details_page = None
            content_div_element = details_page_soup.find('div', id='content') 
            scope_for_pdf_search = content_div_element if content_div_element else details_page_soup

            if scope_for_pdf_search:
                for anchor_tag in scope_for_pdf_search.find_all('a', href=True):
                    tag_text_content = anchor_tag.get_text(strip=True).lower()
                    if tag_text_content == '[pdf]':
                        pdf_link_on_details_page = urljoin(details_page_actual_url, anchor_tag['href'])
                        break
                if not pdf_link_on_details_page: 
                    generic_pdf_anchor_tag = scope_for_pdf_search.find('a', href=lambda h_val: h_val and str(h_val).lower().endswith('.pdf'))
                    if generic_pdf_anchor_tag:
                         generic_tag_text = generic_pdf_anchor_tag.get_text(strip=True).lower()
                         if generic_tag_text not in ['[supp]', '[supplementary]', '[bib]', '[bibtex]', '[slides]', '[video]']:
                            pdf_link_on_details_page = urljoin(details_page_actual_url, generic_pdf_anchor_tag['href'])
            item_data_dict['pdf_url'] = pdf_link_on_details_page
            item_data_dict['details_fetched_flag'] = True
        except Exception as e: 
            self.log_message(f"Error processing details for {details_page_actual_url}: {str(e)[:100]}", "ERROR")
            item_data_dict['details_fetched_flag'] = True 
            item_data_dict['pdf_url'] = None
            item_data_dict['abstract_text'] = "Error fetching details."
        time.sleep(0.05) 

    def _thread_for_fetching_details(self, items_to_fetch_for, page_url_for_joins):
        total_items_to_process = len(items_to_fetch_for)
        for i, item_data_reference in enumerate(items_to_fetch_for):
            if i % 2 == 0 or i == total_items_to_process - 1: 
                self.status_message_var.set(f"Fetching details: {i+1}/{total_items_to_process}...")
                self.root.update_idletasks()
            
            self._fetch_and_parse_item_details_page(item_data_reference, page_url_for_joins) 
        
        self.log_message(f"Finished fetching details for {total_items_to_process} selected items.")
        self.refresh_display_and_pagination() 
        self.status_message_var.set(f"Details fetched. {len(self.items_for_display_list)} items currently displayed.")
        self.fetch_details_for_selected_button.config(state=tk.NORMAL, text="Fetch Details for SELECTED Items")

    def start_fetch_details_for_selected_thread(self):
        selected_items_for_details = [
            item for item in self.all_items_master_list 
            if item['selected_var'].get() and not item.get('details_fetched_flag')
        ]

        if not selected_items_for_details:
            messagebox.showinfo("No Items or Details Already Fetched", 
                                "No items selected, or details have already been fetched for all selected items.")
            self.refresh_display_and_pagination() 
            return

        self.log_message(f"Starting to fetch details for {len(selected_items_for_details)} selected items...")
        self.fetch_details_for_selected_button.config(state=tk.DISABLED, text="Fetching Details...")
        
        thread = threading.Thread(target=self._thread_for_fetching_details, 
                                  args=(selected_items_for_details, self.list_page_url_var.get()))
        thread.daemon = True
        thread.start()

    def show_selected_abstracts(self):
        selected_items_with_abstract_text = [
            item for item in self.items_for_display_list 
            if item['selected_var'].get() and item.get('abstract_text')
        ]
        if not selected_items_with_abstract_text:
            messagebox.showinfo("No Abstracts", "No items selected, or selected items do not have abstracts (try 'Fetch Details' first).")
            return

        abstract_display_window = tk.Toplevel(self.root)
        abstract_display_window.title("Abstracts of Selected Papers")
        abstract_display_window.geometry("800x600")
        abstract_text_widget = scrolledtext.ScrolledText(abstract_display_window, wrap=tk.WORD, padx=5, pady=5, font=("Arial", 10))
        abstract_text_widget.pack(expand=True, fill=tk.BOTH)
        abstract_text_widget.configure(state='disabled')
        full_abstract_text_content = ""
        for item_dict in selected_items_with_abstract_text:
            full_abstract_text_content += f"TITLE: {item_dict.get('title', 'N/A')}\n"
            full_abstract_text_content += f"ABSTRACT:\n{item_dict.get('abstract_text', 'No abstract available.')}\n"
            full_abstract_text_content += "--------------------------------------------------\n\n"
        abstract_text_widget.configure(state='normal')
        abstract_text_widget.delete(1.0, tk.END)
        abstract_text_widget.insert(tk.END, full_abstract_text_content)
        abstract_text_widget.configure(state='disabled')
        abstract_display_window.transient(self.root)
        abstract_display_window.grab_set()
        self.root.wait_window(abstract_display_window)

    def toggle_select_all_visible(self):
        is_now_selected = self.select_all_var.get()
        
        # Determine which items are currently visible on the page
        start_idx = (self.current_page_num - 1) * self.ITEMS_PER_PAGE if self.current_page_num > 0 else 0
        end_idx = start_idx + self.ITEMS_PER_PAGE
        visible_items_on_page = self.items_for_display_list[start_idx:end_idx]

        for item_data_dict in visible_items_on_page:
            item_data_dict['selected_var'].set(is_now_selected)
        self.refresh_display_and_pagination() 

    def start_download_selected_thread(self):
        items_to_be_downloaded = [
            p_item for p_item in self.items_for_display_list # Check from currently displayed/filtered list
            if p_item['selected_var'].get() and p_item.get('pdf_url')
        ]
        if not items_to_be_downloaded:
            messagebox.showinfo("No Items to Download", 
                                "Please select items with available PDF links to download (try 'Fetch Details' first).")
            return
        download_target_dir = self.download_dir_var.get()
        if not download_target_dir or not os.path.isdir(download_target_dir):
            messagebox.showerror("Directory Error", "Please select a valid download directory.")
            return
        
        self.main_download_all_selected_button.config(state=tk.DISABLED, text="Downloading...")
        self.download_selected_action_button.config(state=tk.DISABLED, text="Downloading...")
        self.log_message(f"Starting download for {len(items_to_be_downloaded)} selected items...")
        thread = threading.Thread(target=self._download_selected_items_logic, args=(items_to_be_downloaded, download_target_dir))
        thread.daemon = True
        thread.start()

    def _download_single_pdf_file(self, pdf_file_url, target_file_path, item_title_for_log):
        try:
            self.log_message(f"Downloading: {item_title_for_log[:70]}...", "DEBUG")
            pdf_response_stream = self.http_session.get(pdf_file_url, stream=True, timeout=120)
            pdf_response_stream.raise_for_status()
            with open(target_file_path, 'wb') as f_out:
                for chunk_data in pdf_response_stream.iter_content(chunk_size=8192): f_out.write(chunk_data)
            self.log_message(f"Downloaded: {os.path.basename(target_file_path)}", "SUCCESS")
            return True
        except requests.exceptions.Timeout: self.log_message(f"Timeout error: {item_title_for_log[:70]}...", "ERROR")
        except requests.exceptions.RequestException as e_req: self.log_message(f"Download error {item_title_for_log[:70]}...: {e_req}", "ERROR")
        except Exception as e_gen: self.log_message(f"Unknown error during download {item_title_for_log[:70]}...: {e_gen}", "ERROR")
        return False

    def _download_selected_items_logic(self, items_to_download_list, target_download_dir):
        num_downloaded_successfully, num_failed_to_download = 0, 0
        for item_data_dict_to_dl in items_to_download_list:
            title_for_filename_creation = item_data_dict_to_dl.get('title', "Unknown_Paper")
            if title_for_filename_creation in ["Unknown_Paper", "No Title", ""] or not title_for_filename_creation.strip():
                 title_for_filename_creation = item_data_dict_to_dl.get('raw_text_main_page', 'Downloaded_Item')[:60]

            base_filename_part = "".join(c if c.isalnum() or c in (' ','.','_','-') else '_' for c in title_for_filename_creation)
            base_filename_part = base_filename_part.strip().replace(' ', '_')
            base_filename_part = re.sub(r'__+', '_', base_filename_part) 
            base_filename_part = base_filename_part[:100] 
            
            final_pdf_filename = base_filename_part + ".pdf"
            if len(base_filename_part.replace("_","").strip()) < 5: 
                url_filename_part = os.path.basename(urlparse(item_data_dict_to_dl['pdf_url']).path)
                if url_filename_part and url_filename_part.lower().endswith(".pdf"): final_pdf_filename = url_filename_part
                else: final_pdf_filename = f"paper_{int(time.time())}_{num_downloaded_successfully}.pdf" 
            
            full_target_filepath = os.path.join(target_download_dir, final_pdf_filename)
            if os.path.exists(full_target_filepath):
                self.log_message(f"Skipped (already exists): {final_pdf_filename}", "INFO")
                continue
            
            if self._download_single_pdf_file(item_data_dict_to_dl['pdf_url'], full_target_filepath, title_for_filename_creation):
                num_downloaded_successfully += 1
            else:
                num_failed_to_download += 1
            time.sleep(0.05) 

        summary_dl_message = f"Download complete! Successfully downloaded {num_downloaded_successfully} items."
        if num_failed_to_download > 0: summary_dl_message += f" Failed to download {num_failed_to_download} items."
        self.log_message(summary_dl_message, "INFO")
        if num_failed_to_download > 0: messagebox.showwarning("Download Complete with Errors", summary_dl_message)
        else: messagebox.showinfo("Download Complete", summary_dl_message)
        
        self.main_download_all_selected_button.config(state=tk.NORMAL, text="Download All Selected Items (with PDF)")
        self.download_selected_action_button.config(state=tk.NORMAL, text="Download PDFs (Selected)")
        self.status_message_var.set("Ready")

class ToolTip:
    def __init__(self, widget_ref, text_func): # Changed from text_generator_func
        self.widget = widget_ref
        self.text_func = text_func # Changed from text_generator_func
        self.tooltip_popup_window = None
        self.show_timer_id = None 
        self.hide_timer_id = None 
        self.widget.bind("<Enter>", self.schedule_tooltip_show)
        self.widget.bind("<Leave>", self.schedule_tooltip_hide)
        self.widget.bind("<Button-1>", lambda e: self.hide_tooltip_immediately())

    def schedule_tooltip_show(self, event_data):
        self.cancel_tooltip_hide_timer() 
        if self.tooltip_popup_window: return 
        self.show_timer_id = self.widget.after(700, lambda: self.display_tooltip_now(event_data))

    def display_tooltip_now(self, event_data):
        if self.tooltip_popup_window: self.tooltip_popup_window.destroy() 
        try: tooltip_text_content = self.text_func()
        except Exception: return
        if not tooltip_text_content: return
        
        cursor_x, cursor_y = event_data.x_root + 20, event_data.y_root + 15
        self.tooltip_popup_window = tk.Toplevel(self.widget)
        self.tooltip_popup_window.wm_overrideredirect(True)
        self.tooltip_popup_window.wm_attributes("-topmost", True)
        
        tooltip_label_widget = ttk.Label(self.tooltip_popup_window, text=tooltip_text_content, justify='left',
                                         background="#FFFFE0", relief="solid", borderwidth=1, wraplength=600, padding=5)
        tooltip_label_widget.pack(ipadx=1)
        
        self.tooltip_popup_window.update_idletasks() 
        popup_width, popup_height = self.tooltip_popup_window.winfo_width(), self.tooltip_popup_window.winfo_height()
        screen_total_width, screen_total_height = self.widget.winfo_screenwidth(), self.widget.winfo_screenheight()

        if cursor_x + popup_width > screen_total_width: cursor_x = screen_total_width - popup_width - 10
        if cursor_y + popup_height > screen_total_height: cursor_y = event_data.y_root - popup_height - 10 
        if cursor_x < 0: cursor_x = 10
        if cursor_y < 0: cursor_y = 10
        
        self.tooltip_popup_window.wm_geometry(f"+{int(cursor_x)}+{int(cursor_y)}")
        self.tooltip_popup_window.bind("<Leave>", lambda e: self.hide_tooltip_immediately()) 
        tooltip_label_widget.bind("<Leave>", lambda e: self.hide_tooltip_immediately())

    def schedule_tooltip_hide(self, event_data=None):
        self.cancel_tooltip_show_timer() 
        if self.tooltip_popup_window:
             self.hide_timer_id = self.widget.after(150, self.check_mouse_position_and_hide)

    def check_mouse_position_and_hide(self):
        if self.tooltip_popup_window:
            try:
                parent_widget_x, parent_widget_y = self.widget.winfo_rootx(), self.widget.winfo_rooty()
                parent_widget_w, parent_widget_h = self.widget.winfo_width(), self.widget.winfo_height()
                tooltip_x, tooltip_y = self.tooltip_popup_window.winfo_rootx(), self.tooltip_popup_window.winfo_rooty()
                tooltip_w, tooltip_h = self.tooltip_popup_window.winfo_width(), self.tooltip_popup_window.winfo_height()
                current_mouse_x, current_mouse_y = self.widget.winfo_pointerxy()
                mouse_on_parent_widget = (parent_widget_x <= current_mouse_x < parent_widget_x + parent_widget_w and
                                          parent_widget_y <= current_mouse_y < parent_widget_y + parent_widget_h)
                mouse_on_tooltip_window = (tooltip_x <= current_mouse_x < tooltip_x + tooltip_w and
                                           tooltip_y <= current_mouse_y < tooltip_y + tooltip_h)
                if not mouse_on_parent_widget and not mouse_on_tooltip_window:
                    self.hide_tooltip_immediately()
                else: 
                    self.hide_timer_id = self.widget.after(150, self.check_mouse_position_and_hide)
            except tk.TclError: 
                self.hide_tooltip_immediately()

    def hide_tooltip_immediately(self, event_data=None):
        self.cancel_tooltip_show_timer()
        self.cancel_tooltip_hide_timer()
        if self.tooltip_popup_window:
            try: self.tooltip_popup_window.destroy()
            except tk.TclError: pass 
        self.tooltip_popup_window = None

    def cancel_tooltip_show_timer(self):
        if self.show_timer_id:
            try: self.widget.after_cancel(self.show_timer_id)
            except tk.TclError: pass
            self.show_timer_id = None
            
    def cancel_tooltip_hide_timer(self):
        if self.hide_timer_id:
            try: self.widget.after_cancel(self.hide_timer_id)
            except tk.TclError: pass
            self.hide_timer_id = None

if __name__ == '__main__':
    main_window = tk.Tk()
    try: 
        app_style = ttk.Style(main_window)
        available_system_themes = app_style.theme_names() 
        preferred_ui_themes = ['vista', 'xpnative', 'clam',  'alt', 'default'] 
        for theme_name in preferred_ui_themes:
            if theme_name in available_system_themes:
                try: app_style.theme_use(theme_name)
                except tk.TclError: continue 
                else: break 
    except Exception: pass 
    
    app_instance = PaperDownloaderApp(main_window)
    main_window.mainloop()
