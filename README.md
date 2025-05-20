# Python Paper Downloader GUI

A desktop application with a graphical user interface (GUI) for finding, filtering, and downloading academic papers from web pages, primarily designed for sites like The CVF's Open Access.

## Description

This application allows users to:
1.  Fetch an initial list of paper entries (titles, links to detail pages) from a given URL (e.g., a conference proceedings page).
2.  Select specific items from this list.
3.  Fetch detailed information (direct PDF link, abstract) for the selected items by visiting their respective detail pages.
4.  Filter the list of papers based on year and keywords (searches in title and abstract, if available).
5.  View abstracts of selected papers that have had their details fetched.
6.  Download PDF versions of selected papers for which a direct PDF link was found.

The application uses a multi-threaded approach for network operations (fetching item lists and details) to keep the UI responsive.

## Features

* **GUI Interface:** Built with Tkinter and ttk for a user-friendly experience.
* **Step-by-Step Workflow:**
    1.  Find initial items from a main list URL.
    2.  Select items of interest.
    3.  Fetch full details (PDF link, Abstract) for *selected* items.
    4.  Filter the list based on year and keywords.
    5.  View abstracts or download PDFs for selected, fully-detailed items.
* **Pagination:** Displays results in pages for easier navigation of large lists.
* **Filtering:** Filter by publication year and keywords in titles/abstracts.
* **Abstract Viewer:** Display abstracts of selected papers in a separate window.
* **Selective Downloading:** Download only the papers you have selected and for which a PDF link has been successfully retrieved.
* **Logging:** Provides a log of actions and errors.
* **Responsive UI:** Network operations run in separate threads.

## Requirements

* Python 3.7+
* The following Python libraries:
    * `requests` (for making HTTP requests)
    * `beautifulsoup4` (for parsing HTML)

## Installation

1.  **Clone the repository (if applicable) or download the script.**
    ```bash
    # git clone <repository_url>
    # cd <repository_directory>
    ```

2.  **Create a virtual environment (recommended):**
    ```bash
    python -m venv venv
    ```
    * On Windows:
        ```bash
        venv\Scripts\activate
        ```
    * On macOS/Linux:
        ```bash
        source venv/bin/activate
        ```

3.  **Install the required libraries:**

    ```bash
    pip install -r requirements.txt
    ```
    Or install them directly:
    ```bash
    pip install requests beautifulsoup4
    ```

## Usage

1.  **Run the application:**
    ```bash
    python scripts.py
    ```

2.  **Workflow in the Application:**
    * **Enter List Page URL:** Provide the URL of the main page listing the papers (e.g., `https://openaccess.thecvf.com/CVPR2024?day=all`).
    * **Choose Download Directory:** Select where downloaded PDFs should be saved.
    * **Step 1: Find Items from List Page:** Click this to fetch basic paper information from the list page. Items will appear in the results list. Checkboxes next to each item will be active.
    * **Select Items:** Manually check the boxes next to the items you are interested in.
    * **Step 2: Fetch Details for SELECTED Items:** Click this to retrieve PDF links and abstracts for the items you just selected. The list will update, and items with found PDF links can now be downloaded.
    * **Step 3: Apply Filter (Optional):** Enter year/keywords and click this to filter the *current list of items*. This does not fetch new details.
    * **View Abstracts/Download PDFs:**
        * Use "Show Abstracts (Selected)" to view abstracts of selected items (if details were fetched).
        * Use "Download PDFs (Selected)" (either the one above the list or at the bottom) to download papers.

## Web Scraping Ethics

* This tool is intended for personal, convenient access to publicly available information.
* Be mindful of the website's terms of service and `robots.txt` file.
* Avoid making an excessive number of requests in a short period to prevent overloading the server. The script includes small delays, but responsible usage is key.
* The developers of this script are not responsible for misuse.

## License

This project is open-source. You are free to use, modify, and distribute it. Please consider providing attribution if you build upon it. (e.g., MIT License - you can add a `LICENSE` file if you wish).
