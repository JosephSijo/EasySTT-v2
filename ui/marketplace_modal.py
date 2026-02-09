import tkinter as tk
from tkinter import ttk, messagebox
from typing import List, Dict, Any
from colorama import Fore

class MarketplaceModal:
    """
    Plugin Marketplace Modal for EasySTT.
    Displays available plugins from the remote registry.
    """
    
    def __init__(self, parent, engine):
        self.parent = parent
        self.engine = engine
        
        # Window Setup (Frameless)
        self.root = tk.Toplevel(parent)
        self.root.overrideredirect(True)
        self.root.geometry("600x720")
        self.root.configure(bg="#0a0a0a")
        self.root.transient(parent)
        self.root.grab_set()
        
        # Window Dragging State
        self._drag_data = {"x": 0, "y": 0}
        
        # Appearance (Obsidian)
        self.colors = {
            "bg": "#0a0a0a",
            "surface": "#121212",
            "accent": "#007acc",
            "text": "#ffffff",
            "secondary": "#666666",
            "amber": "#ff9800",
            "green": "#4caf50"
        }
        
        self._build_ui()
        self._load_plugins()

    def _build_ui(self):
        # 0. Custom Title Bar
        self.title_bar = tk.Frame(self.root, bg=self.colors["bg"], height=35)
        self.title_bar.pack(fill="x", side="top")
        self.title_bar.bind("<Button-1>", self._start_drag)
        self.title_bar.bind("<B1-Motion>", self._do_drag)

        tk.Label(self.title_bar, text=" 🛍️ MARKETPLACE", font=("Segoe UI", 9, "bold"),
                 bg=self.colors["bg"], fg="#ffffff").pack(side="left", padx=10)

        tk.Button(self.title_bar, text="✕", font=("Segoe UI", 8),
                  bg=self.colors["bg"], fg="#666666", borderwidth=0, cursor="hand2",
                  activebackground="#ff5252", activeforeground="white",
                  command=self.root.destroy, padx=10).pack(side="right")

        # Header
        header = tk.Frame(self.root, bg=self.colors["bg"], pady=10)
        header.pack(fill="x")
        
        tk.Label(header, text="🛍️ Plugin Marketplace", 
                 font=("Segoe UI", 18, "bold"), 
                 bg=self.colors["bg"], fg="white").pack()
        
        tk.Label(header, text="Enhance transcription with specialized vocabularies.",
                 font=("Segoe UI", 10), 
                 bg=self.colors["bg"], fg=self.colors["secondary"]).pack()
        
        # Search / Filter Bar
        filter_frame = tk.Frame(self.root, bg=self.colors["bg"], padx=20, pady=10)
        filter_frame.pack(fill="x")
        
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *args: self._filter_plugins())
        
        search_entry = tk.Entry(filter_frame, textvariable=self.search_var,
                               bg=self.colors["surface"], fg="white", 
                               insertbackground="white", font=("Segoe UI", 11),
                               borderwidth=0, highlightthickness=1, 
                               highlightbackground="#444444")
        search_entry.pack(fill="x", side="left", expand=True)
        search_entry.insert(0, "Search plugins...")
        search_entry.bind("<FocusIn>", lambda e: search_entry.delete(0, tk.END) if search_entry.get() == "Search plugins..." else None)

        # Scrollable Plugin List
        self.container = tk.Frame(self.root, bg=self.colors["bg"])
        self.container.pack(fill="both", expand=True, padx=20, pady=10)
        
        self.canvas = tk.Canvas(self.container, bg=self.colors["bg"], 
                               highlightthickness=0, borderwidth=0)
        self.scrollbar = ttk.Scrollbar(self.container, orient="vertical", 
                                      command=self.canvas.yview)
        self.scroll_inner = tk.Frame(self.canvas, bg=self.colors["bg"])
        
        self.scroll_inner.bind("<Configure>", 
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        
        self.canvas.create_window((0, 0), window=self.scroll_inner, anchor="nw", width=540)
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        
        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")
        
        # Mousewheel support
        self.canvas.bind_all("<MouseWheel>", lambda e: self.canvas.yview_scroll(int(-1*(e.delta/120)), "units"))

    def _load_plugins(self):
        """Fetches registry data and populates the UI."""
        self.plugins_data = self.engine.marketplace.fetch_registry()
        self._display_plugins(self.plugins_data)

    def _display_plugins(self, plugins: List[Dict[str, Any]]):
        # Clear existing
        for widget in self.scroll_inner.winfo_children():
            widget.destroy()
            
        if not plugins:
            tk.Label(self.scroll_inner, text="No plugins found.", 
                     bg=self.colors["bg"], fg="white", pady=20).pack()
            return
            
        for plugin in plugins:
            self._build_plugin_card(plugin)

    def _build_plugin_card(self, plugin: Dict[str, Any]):
        card = tk.Frame(self.scroll_inner, bg=self.colors["surface"], 
                       padx=15, pady=15, highlightthickness=1, 
                       highlightbackground="#444444")
        card.pack(fill="x", pady=10)
        
        # Left side: Icon/Info
        info_frame = tk.Frame(card, bg=self.colors["surface"])
        info_frame.pack(side="left", fill="both", expand=True)
        
        title_row = tk.Frame(info_frame, bg=self.colors["surface"])
        title_row.pack(fill="x")
        
        tk.Label(title_row, text=plugin["name"], font=("Segoe UI", 12, "bold"),
                 bg=self.colors["surface"], fg="white").pack(side="left")
        
        tier_color = self.colors["amber"] if plugin["tier"] == "PRO" else self.colors["accent"]
        tk.Label(title_row, text=f" {plugin['tier']} ", font=("Segoe UI", 8, "bold"),
                 bg=tier_color, fg="white", padx=5).pack(side="left", padx=10)
        
        tk.Label(info_frame, text=f"by {plugin['author']} • {plugin['category']}", 
                 font=("Segoe UI", 9), bg=self.colors["surface"], 
                 fg=self.colors["secondary"]).pack(anchor="w", pady=(2, 5))
        
        desc = plugin["description"]
        if len(desc) > 80: desc = desc[:77] + "..."
        tk.Label(info_frame, text=desc, font=("Segoe UI", 9), 
                 bg=self.colors["surface"], fg="#dddddd", wraplength=400, 
                 justify="left").pack(anchor="w")
        
        # Right side: Actions
        action_frame = tk.Frame(card, bg=self.colors["surface"])
        action_frame.pack(side="right", padx=(20, 0))
        
        price_text = plugin["price"]
        tk.Label(action_frame, text=price_text, font=("Segoe UI", 11, "bold"),
                 bg=self.colors["surface"], fg="white").pack(pady=(0, 10))
        
        is_installed = self.engine.plugins.is_installed(plugin["id"])
        btn_text = "INSTALLED" if is_installed else "INSTALL"
        btn_state = "disabled" if is_installed else "normal"
        btn_bg = "#444444" if is_installed else self.colors["accent"]
        
        btn = tk.Button(action_frame, text=btn_text, state=btn_state,
                       bg=btn_bg, fg="white", font=("Segoe UI", 9, "bold"),
                       borderwidth=0, cursor="hand2", padx=15, pady=5,
                       command=lambda p=plugin: self._install_plugin(p))
        btn.pack()
        
        # Rating
        tk.Label(action_frame, text=f"⭐ {plugin['rating']}", font=("Segoe UI", 8),
                 bg=self.colors["surface"], fg=self.colors["amber"]).pack(pady=(5, 0))

    def _filter_plugins(self):
        query = self.search_var.get().lower()
        if query == "search plugins...": return
        
        filtered = [p for p in self.plugins_data if 
                    query in p["name"].lower() or 
                    query in p["category"].lower() or 
                    query in p["description"].lower()]
        self._display_plugins(filtered)

    def _install_plugin(self, plugin: Dict[str, Any]):
        """Trigger installation of a plugin."""
        if plugin["tier"] == "PRO" and not self.engine.license.is_pro():
            upgrade = messagebox.askyesno("Pro Extension", 
                                 f"'{plugin['name']}' requires a Professional subscription.\n\n"
                                 f"Would you like to upgrade to PRO now for $19/mo?")
            if upgrade:
                self._upgrade_checkout()
            return
            
        print(f"{Fore.MAGENTA}[Marketplace] Installing plugin: {plugin['name']}...")
        confirm = messagebox.askyesno("Confirm Install", 
                                    f"Do you want to install '{plugin['name']}'?\nSize: {plugin['size']}")
        
        if confirm:
            success = self.engine.plugins.install_remote(plugin)
            if success:
                messagebox.showinfo("Success", f"{plugin['name']} has been installed and activated!")
                self.root.destroy()
                # Refresh Ecosystem view in MainWindow
                if hasattr(self.parent, "after"):
                    self.parent.after(100, lambda: self.engine.preload_model()) # Re-load new vocabs
                    self.parent.after(200, lambda: self.parent._update_ecosystem_view())
            else:
                messagebox.showerror("Error", f"Failed to install {plugin['name']}.")

    def _upgrade_checkout(self):
        """Simulate a secure checkout flow."""
        checkout = tk.Toplevel(self.root)
        checkout.title("Secure Checkout")
        checkout.geometry("400x500")
        checkout.configure(bg="#1a1a1a")
        
        tk.Label(checkout, text="💳 PRO UPGRADE", font=("Segoe UI", 14, "bold"), 
                 bg="#1a1a1a", fg="white", pady=20).pack()
        
        tk.Label(checkout, text="Unlimited Cloud Refinement\nAll Marketplace Plugins\nPriority Support", 
                 font=("Segoe UI", 10), bg="#1a1a1a", fg="#cccccc", pady=10).pack()

        form = tk.Frame(checkout, bg="#1a1a1a", padx=40)
        form.pack(fill="x")
        
        tk.Label(form, text="Cardholder Name", bg="#1a1a1a", fg="#888888").pack(anchor="w")
        tk.Entry(form, bg="#333333", fg="white", borderwidth=0).pack(fill="x", pady=(0, 10))
        
        tk.Label(form, text="Card Number", bg="#1a1a1a", fg="#888888").pack(anchor="w")
        tk.Entry(form, bg="#333333", fg="white", borderwidth=0).pack(fill="x", pady=(0, 10))

        def confirm_pay():
            # Mock success
            self.engine.license.save_license("global", "EASYSTT-PRO-MOCK-2026")
            messagebox.showinfo("Payment Successful", "Welcome to EasySTT PRO!")
            checkout.destroy()
            self._load_plugins() # Refresh view
            
        tk.Button(checkout, text=" COMPLETE PURCHASE ", font=("Segoe UI", 10, "bold"),
                  bg="#007acc", fg="white", borderwidth=0, cursor="hand2",
                  command=confirm_pay, pady=10).pack(pady=30)

    def _start_drag(self, event):
        self._drag_data["x"] = event.x
        self._drag_data["y"] = event.y

    def _do_drag(self, event):
        x = self.root.winfo_x() - self._drag_data["x"] + event.x
        y = self.root.winfo_y() - self._drag_data["y"] + event.y
        self.root.geometry(f"+{x}+{y}")
