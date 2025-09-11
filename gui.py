import tkinter as tk
from tkinter import ttk, messagebox
import threading
import subprocess
import os
from logger import main_logger
import iproperty

class iPropertyGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("iProperty Scraper")
        self.root.geometry("400x300")
        
        # Variables
        self.keyword_var = tk.StringVar(value="ativo suites")
        self.tab_var = tk.StringVar(value="BUY")
        self.state_var = tk.StringVar(value="All States")
        self.scraping_thread = None
        self.stop_scraping = False
        
        self.setup_ui()
        
    def setup_ui(self):
        # Main frame
        main_frame = ttk.Frame(self.root, padding="20")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Keyword input
        ttk.Label(main_frame, text="Keyword:").grid(row=0, column=0, sticky=tk.W, pady=5)
        ttk.Entry(main_frame, textvariable=self.keyword_var, width=30).grid(row=0, column=1, pady=5)
        
        # Tab selection
        ttk.Label(main_frame, text="Tab:").grid(row=1, column=0, sticky=tk.W, pady=5)
        tab_combo = ttk.Combobox(main_frame, textvariable=self.tab_var, values=["BUY", "RENT", "NEW"], width=27)
        tab_combo.grid(row=1, column=1, pady=5)
        
        # State selection
        ttk.Label(main_frame, text="State:").grid(row=2, column=0, sticky=tk.W, pady=5)
        state_combo = ttk.Combobox(main_frame, textvariable=self.state_var, 
                                  values=["All States", "Selangor", "Kuala Lumpur", "Johor", "Penang", "Perak", "Negeri Sembilan", "Melaka", "Pahang", "Sabah", "Sarawak", "Kedah", "Putrajaya", "Kelantan", "Terengganu", "Perlis", "Labuan"], width=27)
        state_combo.grid(row=2, column=1, pady=5)
        
        # Chrome Debug button
        self.chrome_btn = ttk.Button(main_frame, text="Start Chrome Debug", command=self.start_chrome_debug)
        self.chrome_btn.grid(row=3, column=0, columnspan=2, pady=10)
        
        # Start and Stop buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=4, column=0, columnspan=2, pady=10)
        
        self.start_btn = ttk.Button(button_frame, text="Start Scraping", command=self.start_scraping)
        self.start_btn.grid(row=0, column=0, padx=5)
        
        self.stop_btn = ttk.Button(button_frame, text="Stop", command=self.stop_scraping_func, state="disabled")
        self.stop_btn.grid(row=0, column=1, padx=5)
        
        # Status label
        self.status_label = ttk.Label(main_frame, text="Ready to start")
        self.status_label.grid(row=5, column=0, columnspan=2, pady=10)
        
    def start_scraping(self):
        keyword = self.keyword_var.get().strip()
        tab = self.tab_var.get()
        state = self.state_var.get()
        
        if not keyword:
            messagebox.showerror("Error", "Please enter a keyword")
            return
            
        self.start_btn.config(state="disabled")
        self.stop_btn.config(state="normal")
        self.stop_scraping = False
        self.status_label.config(text="Scraping in progress...")
        
        # Run scraping in separate thread
        self.scraping_thread = threading.Thread(target=self.run_scraper, args=(keyword, tab, state))
        self.scraping_thread.daemon = True
        self.scraping_thread.start()
        
    def run_scraper(self, keyword, tab, state):
        try:
            iproperty.LOG = main_logger("iProperty")
            iproperty.stop_flag = lambda: self.stop_scraping
            iproperty.main(keyword, tab, state)
            if self.stop_scraping:
                self.root.after(0, self.scraping_complete, "Scraping stopped by user")
            else:
                self.root.after(0, self.scraping_complete, "Scraping completed successfully!")
        except Exception as e:
            self.root.after(0, self.scraping_complete, f"Error: {str(e)}")
            
    def start_chrome_debug(self):
        try:
            # Create ChromeDebug directory if it doesn't exist
            debug_dir = "C:/ChromeDebug"
            os.makedirs(debug_dir, exist_ok=True)
            
            # Start Chrome with debug mode
            subprocess.Popen([
                "chrome.exe", 
                "--remote-debugging-port=9222", 
                f"--user-data-dir={debug_dir}"
            ])
            self.status_label.config(text="Chrome debug mode started")
            messagebox.showinfo("Success", "Chrome started in debug mode on port 9222")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to start Chrome: {str(e)}")
    
    def stop_scraping_func(self):
        self.stop_scraping = True
        self.status_label.config(text="Stopping scraper...")
        try:
            if hasattr(iproperty, 'driver') and iproperty.driver:
                iproperty.driver.quit()
        except:
            pass
    
    def scraping_complete(self, message):
        self.start_btn.config(state="normal")
        self.stop_btn.config(state="disabled")
        self.status_label.config(text=message)
        messagebox.showinfo("Status", message)

if __name__ == "__main__":
    root = tk.Tk()
    app = iPropertyGUI(root)
    root.mainloop()