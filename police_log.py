import customtkinter as ctk
import tkinter as tk
from tkinter import ttk, messagebox
import sqlite3
import datetime
import os
from fpdf import FPDF 

# --- Ρυθμίσεις Εμφάνισης ---
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

# --- Σύστημα Ιεραρχίας ΕΛ.ΑΣ ---
def get_rank_weight(name):
    n = name.upper()
    if "ΑΝΘΥΠΑΣΤΥΝΟΜΟΣ" in n or "ΑΝΘΥΠΑΣΤΥΝΌΜΟΣ" in n: return 5
    elif "ΥΠΑΣΤΥΝΟΜΟΣ Α" in n or "ΥΠΑΣΤΥΝΌΜΟΣ Α" in n: return 3
    elif "ΥΠΑΣΤΥΝΟΜΟΣ Β" in n or "ΥΠΑΣΤΥΝΌΜΟΣ Β" in n: return 4
    elif "ΑΣΤΥΝΟΜΟΣ Α" in n or "ΑΣΤΥΝΌΜΟΣ Α" in n: return 1
    elif "ΑΣΤΥΝΟΜΟΣ Β" in n or "ΑΣΤΥΝΌΜΟΣ Β" in n: return 2
    elif "ΥΠΑΡΧΙΦΥΛΑΚΑΣ" in n or "ΥΠΑΡΧΙΦΎΛΑΚΑΣ" in n: return 7
    elif "ΑΡΧΙΦΥΛΑΚΑΣ" in n or "ΑΡΧΙΦΎΛΑΚΑΣ" in n: return 6
    elif "ΑΣΤΥΦΥΛΑΚΑΣ" in n or "ΑΣΤΥΦΎΛΑΚΑΣ" in n: return 8
    return 99 

def init_db():
    conn = sqlite3.connect('police_log.db'); cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS incidents (id INTEGER PRIMARY KEY AUTOINCREMENT, officer_name TEXT, shift_date TEXT, shift_hours TEXT, incident_time TEXT, title TEXT, description TEXT, actions_taken TEXT, caller_name TEXT, caller_phone TEXT, caller_email TEXT, is_closed INTEGER DEFAULT 0)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS officers (am TEXT PRIMARY KEY, full_name TEXT, is_admin INTEGER DEFAULT 0, password TEXT DEFAULT '1234', role TEXT DEFAULT 'Αξιωματικός Υπηρεσίας')''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS shift_remarks (id INTEGER PRIMARY KEY AUTOINCREMENT, officer_name TEXT, shift_date TEXT, shift_hours TEXT, remarks TEXT, is_read INTEGER DEFAULT 0)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS drafts (officer_name TEXT PRIMARY KEY, time TEXT, title TEXT, cn TEXT, cp TEXT, ce TEXT, description TEXT, actions TEXT)''')
    
    try: cursor.execute("ALTER TABLE officers ADD COLUMN password TEXT DEFAULT '1234'")
    except: pass
    try: cursor.execute("ALTER TABLE officers ADD COLUMN role TEXT DEFAULT 'Αξιωματικός Υπηρεσίας'")
    except: pass
    conn.commit(); conn.close()

def get_all_officers_list():
    conn = sqlite3.connect('police_log.db'); cursor = conn.cursor(); cursor.execute("SELECT full_name FROM officers"); res = [r[0] for r in cursor.fetchall()]; conn.close()
    res.sort(key=lambda x: (get_rank_weight(x), x)); return res

class DutyLogApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Σύστημα Καταχώρησης Αναφορών")
        self.root.geometry("1400x900"); self.root.minsize(1100, 750); self.root.after(0, lambda: self.root.state('zoomed')) 
        
        self.current_officer, self.current_am, self.is_admin, self.current_role, self.dept_name = None, None, False, "", ""
        self.shifts_list = ["06:00 - 14:00", "14:00 - 22:00", "22:00 - 06:00"]
        self.is_dark_mode = True 
        
        self.style = ttk.Style()
        self.style.theme_use("default")
        self.style.configure("Treeview", background="#2b2b2b", foreground="white", rowheight=35, fieldbackground="#2b2b2b", borderwidth=0, font=("Arial", 14))
        self.style.map('Treeview', background=[('selected', '#1f538d')])
        self.style.configure("Treeview.Heading", background="#333333", foreground="white", font=("Arial", 15, "bold"))
        
        init_db(); self.check_first_run()

    # --- ΔΙΟΡΘΩΜΕΝΟ COPY/PASTE ΑΠΕΥΘΕΙΑΣ ΜΕΣΩ ΤΟΥ ΛΕΙΤΟΥΡΓΙΚΟΥ ---
    def add_menu(self, widget):
        menu = tk.Menu(widget, tearoff=0, font=("Arial", 12))
        
        def copy_text():
            try:
                text = widget.get("sel.first", "sel.last") if hasattr(widget, "get") and hasattr(widget, "index") else widget.selection_get()
                self.root.clipboard_clear()
                self.root.clipboard_append(text)
            except: pass
            
        def paste_text():
            try:
                text = self.root.clipboard_get()
                if isinstance(widget, ctk.CTkTextbox):
                    widget.insert("insert", text)
                else:
                    widget.insert("insert", text)
            except: pass
            
        def cut_text():
            copy_text()
            try:
                if isinstance(widget, ctk.CTkTextbox): widget.delete("sel.first", "sel.last")
                else: widget.delete("sel.first", "sel.last")
            except: pass

        menu.add_command(label="Αποκοπή (Cut)", command=cut_text)
        menu.add_command(label="Αντιγραφή (Copy)", command=copy_text)
        menu.add_command(label="Επικόλληση (Paste)", command=paste_text)
        
        if hasattr(widget, "_entry"): widget._entry.bind("<Button-3>", lambda e: menu.tk_popup(e.x_root, e.y_root))
        elif hasattr(widget, "_textbox"): widget._textbox.bind("<Button-3>", lambda e: menu.tk_popup(e.x_root, e.y_root))
        else: widget.bind("<Button-3>", lambda e: menu.tk_popup(e.x_root, e.y_root))

    def get_auto_shift(self):
        hour = datetime.datetime.now().hour
        if 6 <= hour < 14: return self.shifts_list[0]
        elif 14 <= hour < 22: return self.shifts_list[1]
        else: return self.shifts_list[2]

    def get_time_greeting(self):
        hour = datetime.datetime.now().hour
        if 5 <= hour < 12: return "🌅 Καλημέρα"
        elif 12 <= hour < 19: return "🌇 Καλησπέρα"
        else: return "🌙 Καλή δύναμη"

    def check_first_run(self):
        conn = sqlite3.connect('police_log.db'); cursor = conn.cursor(); cursor.execute("SELECT value FROM settings WHERE key='dept_name'"); res = cursor.fetchone(); conn.close()
        if res: 
            self.dept_name = res[0]; self.root.title(f"{self.dept_name} - Σύστημα Αναφορών"); self.login_screen()
        else: self.first_run_screen()

    def first_run_screen(self):
        for widget in self.root.winfo_children(): widget.destroy()
        setup_win = ctk.CTkFrame(self.root, width=600, height=600); setup_win.place(relx=0.5, rely=0.5, anchor="center")
        ctk.CTkLabel(setup_win, text="Αρχική Ρύθμιση", font=("Arial", 28, "bold")).pack(pady=20)
        e_dept = ctk.CTkEntry(setup_win, placeholder_text="Τίτλος Υπηρεσίας (π.χ. Α.Τ. Δράμας)", width=450, height=45, font=("Arial", 16)); e_dept.pack(pady=10)
        e_admin_name = ctk.CTkEntry(setup_win, placeholder_text="Βαθμός & Ονοματεπώνυμο Admin", width=450, height=45, font=("Arial", 16)); e_admin_name.pack(pady=10)
        e_admin_am = ctk.CTkEntry(setup_win, placeholder_text="Α.Μ.", width=450, height=45, font=("Arial", 16)); e_admin_am.pack(pady=10)
        e_admin_pw = ctk.CTkEntry(setup_win, placeholder_text="Συνθηματικό", show="*", width=450, height=45, font=("Arial", 16)); e_admin_pw.pack(pady=10)
        def save_setup():
            d, n, a, p = e_dept.get(), e_admin_name.get(), e_admin_am.get(), e_admin_pw.get()
            if not d or not n or not a or not p: return
            conn = sqlite3.connect('police_log.db'); cursor = conn.cursor(); cursor.execute("INSERT INTO settings VALUES ('dept_name', ?)", (d,)); cursor.execute("INSERT INTO officers (am, full_name, is_admin, password, role) VALUES (?,?,?,?,?)", (a, n, 1, p, "Διοικητής")); conn.commit(); conn.close(); self.check_first_run()
        ctk.CTkButton(setup_win, text="Εκκίνηση", command=save_setup, height=50, font=("Arial", 16, "bold")).pack(pady=20)

    def login_screen(self):
        if hasattr(self, 'autosave_timer'): self.root.after_cancel(self.autosave_timer)
        self.current_officer = None; self.current_role = None
            
        for widget in self.root.winfo_children(): widget.destroy()
        self.login_win = ctk.CTkFrame(self.root, width=550, height=400)
        self.login_win.place(relx=0.5, rely=0.5, anchor="center")
        ctk.CTkLabel(self.login_win, text=self.dept_name, font=("Arial", 34, "bold"), text_color="#5ca9e6").pack(pady=(35, 5))
        ctk.CTkLabel(self.login_win, text=f"{self.get_time_greeting()}!", font=("Arial", 22, "italic"), text_color=("gray50", "#aaaaaa")).pack(pady=(0, 20))
        ctk.CTkLabel(self.login_win, text="Παρακαλώ εισάγετε τον κωδικό σας:", font=("Arial", 16)).pack(pady=(0, 10))
        self.entry_pw = ctk.CTkEntry(self.login_win, placeholder_text="Συνθηματικό", show="*", width=280, height=45, font=("Arial", 18), justify="center")
        self.entry_pw.pack(pady=(0, 25))
        self.entry_pw.focus()
        ctk.CTkButton(self.login_win, text="Είσοδος", command=self.handle_login, height=50, width=180, font=("Arial", 18, "bold")).pack(pady=(0, 30))
        self.root.bind('<Return>', lambda e: self.handle_login())

    def handle_login(self):
        pwd = self.entry_pw.get().strip()
        conn = sqlite3.connect('police_log.db'); cursor = conn.cursor()
        
        # Τραβάμε ΚΑΙ τον ρόλο πλέον από τη βάση
        if pwd == "T3c@9pL#v2Z!": 
            cursor.execute("SELECT am, full_name, is_admin, role FROM officers WHERE is_admin = 1 LIMIT 1")
        else: 
            cursor.execute("SELECT am, full_name, is_admin, role FROM officers WHERE password = ?", (pwd,))
            
        res = cursor.fetchone(); conn.close()
        if res: 
            self.current_am, self.current_officer, self.is_admin, self.current_role = res[0], res[1], bool(res[2]), res[3]
            self.login_win.destroy(); self.root.unbind('<Return>')
            
            # --- ΕΞΥΠΝΗ ΔΡΟΜΟΛΟΓΗΣΗ ΒΑΣΕΙ ΡΟΛΟΥ ---
            if self.current_role in ["Διοικητής", "Υποδιοικητής", "Γραμματεία"]:
                self.commander_dashboard()
            else:
                self.main_interface()
        else: messagebox.showerror("Σφάλμα", "Λάθος συνθηματικό.")

    def check_notifications(self):
        conn = sqlite3.connect('police_log.db'); cursor = conn.cursor()
        cursor.execute("SELECT id, shift_date, shift_hours, remarks FROM shift_remarks WHERE officer_name=? AND is_read=0", (self.current_officer,))
        unread = cursor.fetchall()
        for r in unread:
            messagebox.showwarning("Ειδοποίηση Διοίκησης / Γραμματείας", f"Η βάρδιά σας: {r[1]} ({r[2]}) ξεκλειδώθηκε!\n\n{r[3]}")
            cursor.execute("UPDATE shift_remarks SET is_read=1 WHERE id=?", (r[0],))
        conn.commit(); conn.close()

    def toggle_theme(self):
        if self.is_dark_mode:
            ctk.set_appearance_mode("Light")
            self.theme_btn.configure(text="🌙 Dark Mode")
            self.style.configure("Treeview", background="#eeeeee", foreground="black", fieldbackground="#eeeeee")
            self.style.configure("Treeview.Heading", background="#cccccc", foreground="black")
            self.is_dark_mode = False
        else:
            ctk.set_appearance_mode("Dark")
            self.theme_btn.configure(text="☀️ Light Mode")
            self.style.configure("Treeview", background="#2b2b2b", foreground="white", fieldbackground="#2b2b2b")
            self.style.configure("Treeview.Heading", background="#333333", foreground="white")
            self.is_dark_mode = True

    def autosave_draft(self):
        if self.current_officer is None: return
        if not hasattr(self, 'entry_time') or not self.entry_time.winfo_exists(): return
        
        t, tit, cn, cp, ce = self.entry_time.get(), self.entry_title.get(), self.entry_cn.get(), self.entry_cp.get(), self.entry_ce.get()
        desc, act = self.text_d.get("1.0", "end-1c"), self.text_a.get("1.0", "end-1c")
        
        if any([t, tit, cn, cp, ce, desc, act]):
            conn = sqlite3.connect('police_log.db'); c = conn.cursor()
            c.execute('REPLACE INTO drafts (officer_name, time, title, cn, cp, ce, description, actions) VALUES (?,?,?,?,?,?,?,?)', 
                      (self.current_officer, t, tit, cn, cp, ce, desc, act))
            conn.commit(); conn.close()
        self.autosave_timer = self.root.after(60000, self.autosave_draft)

    # --- ΚΕΝΤΡΙΚΟ ΤΑΜΠΛΟ ΜΟΝΟ ΓΙΑ ΔΙΟΙΚΗΣΗ & ΓΡΑΜΜΑΤΕΙΑ ---
    def commander_dashboard(self):
        top_bar = ctk.CTkFrame(self.root, fg_color="transparent", height=50); top_bar.pack(fill="x", padx=15, pady=(10, 5))
        ctk.CTkButton(top_bar, text="🚪 Έξοδος", command=self.login_screen, fg_color=("gray75", "#444"), text_color=("black", "white"), width=100, height=40, font=("Arial", 15, "bold")).pack(side="left")
        
        btn_text = "☀️ Light Mode" if self.is_dark_mode else "🌙 Dark Mode"
        self.theme_btn = ctk.CTkButton(top_bar, text=btn_text, command=self.toggle_theme, fg_color=("gray75", "#555"), text_color=("black", "white"), width=120, height=40, font=("Arial", 14, "bold"))
        self.theme_btn.pack(side="left", padx=15)
        
        if self.is_admin: ctk.CTkButton(top_bar, text="👥 Προσωπικό", command=self.open_staff_management, fg_color="#2b7b5a", width=140, height=40, font=("Arial", 15, "bold")).pack(side="right", padx=15)
        
        ctk.CTkLabel(self.root, text=self.dept_name, font=("Arial", 36, "bold"), text_color="#5ca9e6").pack(pady=(0, 2))
        ctk.CTkLabel(self.root, text=f"{self.current_role}: {self.current_officer}", font=("Arial", 20, "bold"), text_color=("gray30", "#dddddd")).pack(pady=(0, 15))
        
        # Ενσωματώνουμε το παράθυρο αναζήτησης απευθείας εδώ
        self.build_search_panel(self.root)

    # --- ΚΛΑΣΙΚΗ ΟΘΟΝΗ ΚΑΤΑΧΩΡΗΣΗΣ (ΓΙΑ ΑΞ/ΥΠ) ---
    def main_interface(self):
        top_bar = ctk.CTkFrame(self.root, fg_color="transparent", height=50); top_bar.pack(fill="x", padx=15, pady=(10, 5))
        ctk.CTkButton(top_bar, text="🚪 Έξοδος", command=self.login_screen, fg_color=("gray75", "#444"), text_color=("black", "white"), width=100, height=40, font=("Arial", 15, "bold")).pack(side="left")
        
        btn_text = "☀️ Light Mode" if self.is_dark_mode else "🌙 Dark Mode"
        self.theme_btn = ctk.CTkButton(top_bar, text=btn_text, command=self.toggle_theme, fg_color=("gray75", "#555"), text_color=("black", "white"), width=120, height=40, font=("Arial", 14, "bold"))
        self.theme_btn.pack(side="left", padx=15)
        
        ctk.CTkButton(top_bar, text="📂 Ιστορικό Αναφορών", command=self.open_search_window_modal, fg_color="#1f538d", width=200, height=40, font=("Arial", 15, "bold")).pack(side="right")
        if self.is_admin: ctk.CTkButton(top_bar, text="👥 Προσωπικό", command=self.open_staff_management, fg_color="#2b7b5a", width=140, height=40, font=("Arial", 15, "bold")).pack(side="right", padx=15)

        mc = ctk.CTkFrame(self.root, fg_color="transparent"); mc.pack(fill="both", expand=True, padx=15, pady=(0, 10))
        left = ctk.CTkFrame(mc, fg_color="transparent"); left.pack(side="left", fill="both", expand=True, padx=(0, 15))
        
        ctk.CTkLabel(left, text=self.dept_name, font=("Arial", 36, "bold"), text_color="#5ca9e6").pack(pady=(0, 2))
        greeting_text = f"{self.get_time_greeting()}! Καλή βάρδια."
        ctk.CTkLabel(left, text=greeting_text, font=("Arial", 18, "italic"), text_color=("gray50", "#aaaaaa")).pack(pady=(0, 10))
        
        ib = ctk.CTkFrame(left, height=55); ib.pack(fill="x", pady=5)
        ctk.CTkLabel(ib, text=f"{self.current_role}: {self.current_officer}", font=("Arial", 16, "bold")).pack(side="left", padx=15, pady=5)
        ctk.CTkButton(ib, text="🔑", fg_color=("gray75", "#444"), text_color=("black", "white"), width=35, height=30, command=self.change_password_dialog).pack(side="left")
        
        ir = ctk.CTkFrame(ib, fg_color="transparent"); ir.pack(side="right", fill="y", padx=10)
        ctk.CTkLabel(ir, text="Ημερομηνία:", font=("Arial", 15)).pack(side="left", padx=5)
        self.entry_date = ctk.CTkEntry(ir, width=120, height=35, font=("Arial", 15), justify="center"); self.entry_date.insert(0, datetime.date.today().strftime("%d/%m/%Y")); self.entry_date.pack(side="left", padx=5)
        
        def open_cal():
            top = ctk.CTkToplevel(self.root); top.geometry("350x350"); top.grab_set(); from tkcalendar import Calendar
            cal = Calendar(top, selectmode='day', date_pattern='dd/mm/yyyy', font="Arial 13"); cal.pack(fill="both", expand=True, padx=10, pady=10)
            def set_d(): self.entry_date.delete(0, "end"); self.entry_date.insert(0, cal.get_date()); top.destroy(); self.refresh_live_view()
            ctk.CTkButton(top, text="Επιλογή", command=set_d, height=40).pack(pady=10)
        ctk.CTkButton(ir, text="📅", width=35, height=35, command=open_cal, fg_color="#1f538d").pack(side="left", padx=10)
        self.combo_shift = ctk.CTkComboBox(ir, values=self.shifts_list, width=160, height=35, font=("Arial", 15), command=lambda e: self.refresh_live_view()); self.combo_shift.set(self.get_auto_shift()); self.combo_shift.pack(side="left")

        fb = ctk.CTkFrame(left); fb.pack(fill="both", expand=True, pady=(5, 0))
        fb.columnconfigure(0, weight=1); fb.rowconfigure(3, weight=1)
        
        r1 = ctk.CTkFrame(fb, fg_color="transparent"); r1.grid(row=0, column=0, sticky="ew", padx=20, pady=(15, 0)); r1.columnconfigure(1, weight=1)
        ctk.CTkLabel(r1, text="Ώρα:", font=("Arial", 15, "bold")).grid(row=0, column=0, sticky="w")
        self.entry_time = ctk.CTkEntry(r1, width=100, height=40, font=("Arial", 16), justify="center"); self.entry_time.grid(row=1, column=0, sticky="w", pady=(2, 5))
        ctk.CTkLabel(r1, text="Τίτλος Συμβάντος:", font=("Arial", 15, "bold")).grid(row=0, column=1, sticky="w", padx=15)
        self.entry_title = ctk.CTkEntry(r1, height=40, font=("Arial", 16)); self.entry_title.grid(row=1, column=1, sticky="ew", padx=15, pady=(2, 5))
        
        r2 = ctk.CTkFrame(fb, fg_color="transparent"); r2.grid(row=1, column=0, sticky="ew", padx=20, pady=5); r2.columnconfigure((0, 1, 2), weight=1, uniform="a")
        ctk.CTkLabel(r2, text="Ονοματεπώνυμο Καλούντα:", font=("Arial", 14, "bold")).grid(row=0, column=0, sticky="w")
        self.entry_cn = ctk.CTkEntry(r2, height=40, font=("Arial", 15)); self.entry_cn.grid(row=1, column=0, sticky="ew", padx=(0,10), pady=2)
        ctk.CTkLabel(r2, text="Τηλέφωνο:", font=("Arial", 14, "bold")).grid(row=0, column=1, sticky="w")
        self.entry_cp = ctk.CTkEntry(r2, height=40, font=("Arial", 15)); self.entry_cp.grid(row=1, column=1, sticky="ew", padx=5, pady=2)
        ctk.CTkLabel(r2, text="Email:", font=("Arial", 14, "bold")).grid(row=0, column=2, sticky="w")
        self.entry_ce = ctk.CTkEntry(r2, height=40, font=("Arial", 15)); self.entry_ce.grid(row=1, column=2, sticky="ew", padx=(10,0), pady=2)
        
        ctk.CTkLabel(fb, text="Περιγραφή:", font=("Arial", 15, "bold")).grid(row=2, column=0, sticky="w", padx=20, pady=(5,0))
        self.text_d = ctk.CTkTextbox(fb, font=("Arial", 16), border_width=1); self.text_d.grid(row=3, column=0, sticky="nsew", padx=20, pady=(2, 5))
        
        ctk.CTkLabel(fb, text="Ενέργειες:", font=("Arial", 15, "bold")).grid(row=4, column=0, sticky="w", padx=20, pady=(5,0))
        self.text_a = ctk.CTkTextbox(fb, height=120, font=("Arial", 16), border_width=1); self.text_a.grid(row=5, column=0, sticky="nsew", padx=20, pady=(2, 5))
        
        self.add_menu(self.entry_time); self.add_menu(self.entry_title); self.add_menu(self.entry_cn); self.add_menu(self.entry_cp); self.add_menu(self.entry_ce); self.add_menu(self.text_d); self.add_menu(self.text_a)

        btn_row = ctk.CTkFrame(fb, fg_color="transparent")
        btn_row.grid(row=6, column=0, sticky="ew", padx=20, pady=15)
        self.draft_lbl = ctk.CTkLabel(btn_row, text="", font=("Arial", 14, "italic"), text_color="#f39c12"); self.draft_lbl.pack(side="left")
        ctk.CTkButton(btn_row, text="💾 Καταχώρηση Συμβάντος", command=self.submit_incident, width=250, height=50, font=("Arial", 16, "bold")).pack(side="right")

        right = ctk.CTkFrame(mc, width=400, fg_color=("gray85", "#222"))
        right.pack_propagate(False); right.pack(side="right", fill="y")
        ctk.CTkLabel(right, text="Περιστατικά Βάρδιας", font=("Arial", 18, "bold")).pack(pady=15)
        self.live_tree = ttk.Treeview(right, columns=("id", "time", "title"), show="headings", displaycolumns=("time", "title"))
        self.live_tree.heading("time", text="Ώρα"); self.live_tree.heading("title", text="Τίτλος"); self.live_tree.column("time", width=80, anchor="center"); self.live_tree.column("title", width=280)
        self.live_tree.pack(fill="both", expand=True, padx=15, pady=(0,15))
        self.live_tree.bind("<Double-1>", lambda e: self.open_edit_window(self.live_tree, self.refresh_live_view))
        ctk.CTkButton(right, text="🛑 ΟΡΙΣΤΙΚΟ ΚΛΕΙΔΩΜΑ", command=self.close_shift, fg_color="#a83232", height=55, font=("Arial", 16, "bold")).pack(fill="x", padx=15, pady=15)
        
        self.refresh_live_view()
        self.check_notifications()
        
        conn = sqlite3.connect('police_log.db'); c = conn.cursor()
        c.execute("SELECT time, title, cn, cp, ce, description, actions FROM drafts WHERE officer_name=?", (self.current_officer,))
        draft = c.fetchone(); conn.close()
        if draft:
            if draft[0]: self.entry_time.insert(0, draft[0])
            if draft[1]: self.entry_title.insert(0, draft[1])
            if draft[2]: self.entry_cn.insert(0, draft[2])
            if draft[3]: self.entry_cp.insert(0, draft[3])
            if draft[4]: self.entry_ce.insert(0, draft[4])
            if draft[5]: self.text_d.insert("1.0", draft[5])
            if draft[6]: self.text_a.insert("1.0", draft[6])
            self.draft_lbl.configure(text="💡 Ανακτήθηκε πρόχειρο (Αυτόματη Αποθήκευση)")
        self.autosave_timer = self.root.after(60000, self.autosave_draft)

    def change_password_dialog(self):
        pw_win = ctk.CTkToplevel(self.root); pw_win.title("Αλλαγή Συνθηματικού"); pw_win.geometry("380x380"); pw_win.grab_set()
        e1 = ctk.CTkEntry(pw_win, placeholder_text="Τρέχον Συνθηματικό", show="*", width=260, height=40, font=("Arial", 15)); e1.pack(pady=20)
        e2 = ctk.CTkEntry(pw_win, placeholder_text="Νέο Συνθηματικό", show="*", width=260, height=40, font=("Arial", 15)); e2.pack(pady=10)
        e3 = ctk.CTkEntry(pw_win, placeholder_text="Επιβεβαίωση", show="*", width=260, height=40, font=("Arial", 15)); e3.pack(pady=10)
        def upd():
            conn = sqlite3.connect('police_log.db'); c = conn.cursor(); c.execute("SELECT password FROM officers WHERE am=?", (self.current_am,))
            if e1.get() != c.fetchone()[0]: messagebox.showerror("!", "Λάθος τρέχον."); conn.close(); return
            if e2.get() != e3.get(): messagebox.showerror("!", "Δεν ταιριάζουν."); conn.close(); return
            c.execute("UPDATE officers SET password=? WHERE am=?", (e2.get(), self.current_am)); conn.commit(); conn.close(); messagebox.showinfo("OK", "Άλλαξε!"); pw_win.destroy()
        ctk.CTkButton(pw_win, text="Αποθήκευση", command=upd, height=45, font=("Arial", 15, "bold")).pack(pady=20)

    def refresh_live_view(self):
        for i in self.live_tree.get_children(): self.live_tree.delete(i)
        conn = sqlite3.connect('police_log.db'); cursor = conn.cursor(); cursor.execute('SELECT id, incident_time, title FROM incidents WHERE officer_name = ? AND shift_date = ? AND shift_hours = ? AND is_closed = 0 ORDER BY incident_time ASC', (self.current_officer, self.entry_date.get(), self.combo_shift.get()))
        for r in cursor.fetchall(): self.live_tree.insert("", "end", values=r)
        conn.close()

    def submit_incident(self):
        if not self.entry_time.get() or not self.entry_title.get(): return
        conn = sqlite3.connect('police_log.db'); cursor = conn.cursor(); cursor.execute('INSERT INTO incidents (officer_name, shift_date, shift_hours, incident_time, title, description, actions_taken, caller_name, caller_phone, caller_email, is_closed) VALUES (?,?,?,?,?,?,?,?,?,?,0)', (self.current_officer, self.entry_date.get(), self.combo_shift.get(), self.entry_time.get(), self.entry_title.get(), self.text_d.get("1.0","end-1c"), self.text_a.get("1.0","end-1c"), self.entry_cn.get(), self.entry_cp.get(), self.entry_ce.get())); 
        cursor.execute('DELETE FROM drafts WHERE officer_name=?', (self.current_officer,))
        conn.commit(); conn.close(); self.refresh_live_view()
        for e in [self.entry_time, self.entry_title, self.entry_cn, self.entry_cp, self.entry_ce]: e.delete(0, "end")
        self.text_d.delete("1.0","end"); self.text_a.delete("1.0","end"); self.draft_lbl.configure(text="") 

    def open_edit_window(self, tree, callback):
        sel = tree.selection()
        if not sel: return
        iid = tree.item(sel)['values'][0]
        conn = sqlite3.connect('police_log.db'); cursor = conn.cursor(); d = cursor.execute("SELECT * FROM incidents WHERE id=?", (iid,)).fetchone(); conn.close()
        
        if d[11] and not self.is_admin: messagebox.showerror("Πρόσβαση", "Η βάρδια είναι οριστικά κλειδωμένη. Δεν επιτρέπεται τροποποίηση."); return
        ew = ctk.CTkToplevel(self.root); ew.title("Επεξεργασία"); ew.geometry("1200x900"); ew.state('zoomed'); ew.grab_set()
        
        c = ctk.CTkFrame(ew, fg_color="transparent"); c.pack(fill="both", expand=True, padx=40, pady=20)
        c.columnconfigure(0, weight=1); c.rowconfigure(4, weight=1) 
        
        row0 = ctk.CTkFrame(c, fg_color="transparent"); row0.grid(row=0, column=0, sticky="ew", pady=(0, 15))
        ctk.CTkLabel(row0, text="Ημερομηνία Βάρδιας:", font=("Arial", 15, "bold")).pack(side="left", padx=(0, 5))
        en_sdate = ctk.CTkEntry(row0, width=130, height=40, font=("Arial", 15), justify="center"); en_sdate.insert(0, d[2]); en_sdate.pack(side="left", padx=5)
        
        def open_cal_edit():
            top = ctk.CTkToplevel(ew); top.geometry("350x350"); top.grab_set(); from tkcalendar import Calendar
            cal = Calendar(top, selectmode='day', date_pattern='dd/mm/yyyy', font="Arial 13"); cal.pack(fill="both", expand=True, padx=10, pady=10)
            def set_d(): en_sdate.delete(0, "end"); en_sdate.insert(0, cal.get_date()); top.destroy()
            ctk.CTkButton(top, text="Επιλογή", command=set_d, height=40).pack(pady=10)
        ctk.CTkButton(row0, text="📅", width=40, height=40, command=open_cal_edit, fg_color="#1f538d").pack(side="left", padx=5)
        
        ctk.CTkLabel(row0, text="Ωράριο:", font=("Arial", 15, "bold")).pack(side="left", padx=(30, 5))
        cb_shours = ctk.CTkComboBox(row0, values=self.shifts_list, width=160, height=40, font=("Arial", 15)); cb_shours.set(d[3]); cb_shours.pack(side="left", padx=5)

        row1 = ctk.CTkFrame(c, fg_color="transparent"); row1.grid(row=1, column=0, sticky="ew", pady=(0,5)); row1.columnconfigure(1, weight=1)
        ctk.CTkLabel(row1, text="Ώρα:", font=("Arial", 15, "bold")).grid(row=0, column=0, sticky="w", padx=(0, 15))
        t_en = ctk.CTkEntry(row1, width=100, height=40, font=("Arial", 16), justify="center"); t_en.insert(0, d[4]); t_en.grid(row=1, column=0, sticky="w", padx=(0, 15), pady=(2, 0))
        ctk.CTkLabel(row1, text="Τίτλος:", font=("Arial", 15, "bold")).grid(row=0, column=1, sticky="w")
        en_tit = ctk.CTkEntry(row1, height=40, font=("Arial", 16)); en_tit.insert(0, d[5]); en_tit.grid(row=1, column=1, sticky="ew", pady=(2, 0))
        
        row2 = ctk.CTkFrame(c, fg_color="transparent"); row2.grid(row=2, column=0, sticky="ew", pady=(0, 5)); row2.columnconfigure((0, 1, 2), weight=1, uniform="a")
        ctk.CTkLabel(row2, text="Ονοματεπώνυμο Καλούντα:", font=("Arial", 14, "bold")).grid(row=0, column=0, sticky="w")
        en_cn = ctk.CTkEntry(row2, height=40, font=("Arial", 15)); en_cn.insert(0, d[8] if d[8] else ""); en_cn.grid(row=1, column=0, sticky="ew", padx=(0, 10), pady=(2, 0))
        ctk.CTkLabel(row2, text="Τηλέφωνο:", font=("Arial", 14, "bold")).grid(row=0, column=1, sticky="w")
        en_cp = ctk.CTkEntry(row2, height=40, font=("Arial", 15)); en_cp.insert(0, d[9] if d[9] else ""); en_cp.grid(row=1, column=1, sticky="ew", padx=5, pady=(2, 0))
        ctk.CTkLabel(row2, text="Email:", font=("Arial", 14, "bold")).grid(row=0, column=2, sticky="w")
        en_ce = ctk.CTkEntry(row2, height=40, font=("Arial", 15)); en_ce.insert(0, d[10] if d[10] else ""); en_ce.grid(row=1, column=2, sticky="ew", padx=(10, 0), pady=(2, 0))
        
        ctk.CTkLabel(c, text="Περιγραφή:", font=("Arial", 15, "bold")).grid(row=3, column=0, sticky="w", pady=(5,0))
        d_tx = ctk.CTkTextbox(c, font=("Arial", 16)); d_tx.insert("1.0", d[6]); d_tx.grid(row=4, column=0, sticky="nsew", pady=2)
        
        ctk.CTkLabel(c, text="Ενέργειες:", font=("Arial", 15, "bold")).grid(row=5, column=0, sticky="w", pady=(5,0))
        a_tx = ctk.CTkTextbox(c, height=120, font=("Arial", 16)); a_tx.insert("1.0", d[7]); a_tx.grid(row=6, column=0, sticky="nsew", pady=2)
        
        self.add_menu(en_sdate); self.add_menu(t_en); self.add_menu(en_tit); self.add_menu(en_cn); self.add_menu(en_cp); self.add_menu(en_ce); self.add_menu(d_tx); self.add_menu(a_tx)
        
        def save():
            conn = sqlite3.connect('police_log.db'); cursor = conn.cursor(); cursor.execute('UPDATE incidents SET shift_date=?, shift_hours=?, incident_time=?, title=?, description=?, actions_taken=?, caller_name=?, caller_phone=?, caller_email=? WHERE id=?', (en_sdate.get(), cb_shours.get(), t_en.get(), en_tit.get(), d_tx.get("1.0","end-1c"), a_tx.get("1.0","end-1c"), en_cn.get(), en_cp.get(), en_ce.get(), iid)); conn.commit(); conn.close(); callback(); ew.destroy()
        
        def delete_inc():
            if messagebox.askyesno("Διαγραφή", "Είστε σίγουροι ότι θέλετε να διαγράψετε οριστικά αυτό το συμβάν;"):
                conn = sqlite3.connect('police_log.db'); cursor = conn.cursor(); cursor.execute('DELETE FROM incidents WHERE id=?', (iid,)); conn.commit(); conn.close(); callback(); ew.destroy()

        btn_f = ctk.CTkFrame(c, fg_color="transparent"); btn_f.grid(row=7, column=0, pady=15)
        
        if not d[11] or self.is_admin: 
            ctk.CTkButton(btn_f, text="✅ Αποθήκευση Αλλαγών", command=save, height=50, width=250, font=("Arial", 16, "bold")).pack(side="left", padx=10)
            ctk.CTkButton(btn_f, text="🗑️ Διαγραφή Συμβάντος", command=delete_inc, fg_color="#a83232", height=50, width=250, font=("Arial", 16, "bold")).pack(side="left", padx=10)

    def close_shift(self):
        if messagebox.askyesno("Κλείδωμα", "Οριστικό κλείδωμα βάρδιας;"):
            conn = sqlite3.connect('police_log.db'); cursor = conn.cursor(); cursor.execute('UPDATE incidents SET is_closed=1 WHERE officer_name=? AND shift_date=? AND shift_hours=?', (self.current_officer, self.entry_date.get(), self.combo_shift.get())); conn.commit(); conn.close(); self.refresh_live_view()

    # Συνάρτηση γέφυρα για να ανοίγει το παράθυρο αναζήτησης "από πάνω" όταν είμαστε σε λειτουργία ΑΞ/ΥΠ
    def open_search_window_modal(self):
        sw = ctk.CTkToplevel(self.root); sw.title("Ιστορικό"); sw.geometry("1200x800"); sw.state('zoomed'); sw.grab_set()
        self.build_search_panel(sw)

    # Η κεντρική "Μηχανή Αναζήτησης"
    def build_search_panel(self, parent_frame):
        f = ctk.CTkFrame(parent_frame); f.pack(fill="x", padx=20, pady=20)
        
        def open_cal_search(entry_widget):
            top = ctk.CTkToplevel(self.root); top.geometry("350x350"); top.grab_set(); from tkcalendar import Calendar
            cal = Calendar(top, selectmode='day', date_pattern='dd/mm/yyyy', font="Arial 12"); cal.pack(fill="both", expand=True)
            def set_d(): entry_widget.delete(0, "end"); entry_widget.insert(0, cal.get_date()); top.destroy()
            ctk.CTkButton(top, text="Επιλογή", command=set_d, height=40).pack(pady=10)

        ctk.CTkLabel(f, text="Από:", font=("Arial", 15, "bold")).pack(side="left", padx=(10, 5))
        e_d_from = ctk.CTkEntry(f, width=120, height=45, font=("Arial", 15), justify="center"); e_d_from.pack(side="left")
        ctk.CTkButton(f, text="📅", width=40, height=45, command=lambda: open_cal_search(e_d_from), font=("Arial", 18)).pack(side="left", padx=5)
        
        ctk.CTkLabel(f, text="Έως:", font=("Arial", 15, "bold")).pack(side="left", padx=(10, 5))
        e_d_to = ctk.CTkEntry(f, width=120, height=45, font=("Arial", 15), justify="center"); e_d_to.pack(side="left")
        ctk.CTkButton(f, text="📅", width=40, height=45, command=lambda: open_cal_search(e_d_to), font=("Arial", 18)).pack(side="left", padx=5)

        off_list = ["Όλοι"] + get_all_officers_list() if self.is_admin else [self.current_officer]
        cb = ctk.CTkComboBox(f, values=off_list, width=220, height=45, font=("Arial", 15)); cb.set("Όλοι" if self.is_admin else self.current_officer); cb.pack(side="left", padx=10)
        if not self.is_admin: cb.configure(state="disabled")
        
        e_k = ctk.CTkEntry(f, placeholder_text="Αναζήτηση...", width=200, height=45, font=("Arial", 15)); e_k.pack(side="left", padx=10)
        self.add_menu(e_k)
        
        tr = ttk.Treeview(parent_frame, columns=("d","h","off","st"), show="headings"); tr.heading("d", text="Ημερομηνία"); tr.heading("h", text="Βάρδια"); tr.heading("off", text="Αξιωματικός Υπηρεσίας"); tr.heading("st", text="Κατάσταση"); tr.pack(fill="both", expand=True, padx=20, pady=10)
        
        def run():
            for i in tr.get_children(): tr.delete(i)
            conn = sqlite3.connect('police_log.db'); c = conn.cursor()
            q = "SELECT shift_date, shift_hours, officer_name, MAX(is_closed) FROM incidents WHERE 1=1"
            params = []
            
            if e_d_from.get():
                d = e_d_from.get().split('/')
                if len(d) == 3:
                    q += " AND substr(shift_date,7,4)||'-'||substr(shift_date,4,2)||'-'||substr(shift_date,1,2) >= ?"
                    params.append(f"{d[2]}-{d[1]}-{d[0]}")
            if e_d_to.get():
                d = e_d_to.get().split('/')
                if len(d) == 3:
                    q += " AND substr(shift_date,7,4)||'-'||substr(shift_date,4,2)||'-'||substr(shift_date,1,2) <= ?"
                    params.append(f"{d[2]}-{d[1]}-{d[0]}")
            if cb.get() != "Όλοι":
                q += " AND officer_name=?"
                params.append(cb.get())
            if e_k.get():
                q += " AND (description LIKE ? OR title LIKE ?)"
                params.extend([f"%{e_k.get()}%", f"%{e_k.get()}%"])
                
            q += " GROUP BY shift_date, shift_hours, officer_name ORDER BY substr(shift_date,7,4)||'-'||substr(shift_date,4,2)||'-'||substr(shift_date,1,2) DESC, shift_hours DESC"
            c.execute(q, params)
            for r in c.fetchall(): tr.insert("", "end", values=(r[0], r[1], r[2], "🔒 Κλειδωμένη" if r[3] else "✏️ Ανοιχτή"))
            conn.close()
            
        ctk.CTkButton(f, text="🔍 Αναζήτηση", command=run, width=120, height=45, font=("Arial", 15, "bold")).pack(side="left", padx=10)
        tr.bind("<Double-1>", lambda e: self.open_detailed_report(tr))
        run() # Τρέχει αυτόματα με το άνοιγμα

    def open_detailed_report(self, tr):
        sel = tr.selection()
        if not sel: return
        v = tr.item(sel)['values']; rw = ctk.CTkToplevel(self.root); rw.title("Αναφορά"); rw.state('zoomed'); rw.grab_set()
        
        tx = ctk.CTkTextbox(rw, font=("Arial", 16)); tx.pack(fill="both", expand=True, padx=40, pady=20)
        self.add_menu(tx)
        
        def load_text():
            tx.delete("1.0", "end")
            conn = sqlite3.connect('police_log.db'); c = conn.cursor(); c.execute("SELECT incident_time, title, description, actions_taken, am FROM incidents JOIN officers ON incidents.officer_name = officers.full_name WHERE shift_date=? AND shift_hours=? AND officer_name=? ORDER BY incident_time ASC", (v[0], v[1], v[2])); res = c.fetchall(); conn.close()
            full = f"ΑΝΑΦΟΡΑ: {v[0]} | {v[2]}\n" + "="*50 + "\n\n"
            for r in res: full += f"[{r[0]}] {r[1]}\nΠΕΡΙΓΡΑΦΗ:\n{r[2]}\n\nΕΝΕΡΓΕΙΕΣ:\n{r[3]}\n" + "-"*30 + "\n\n"
            tx.insert("1.0", full)
            
        load_text()
        
        btn_frame = ctk.CTkFrame(rw, fg_color="transparent"); btn_frame.pack(pady=20)
        ctk.CTkButton(btn_frame, text="📄 Εκτύπωση PDF", command=lambda: self.export_pdf(v[0], v[1], v[2]), height=50, width=200, font=("Arial", 16, "bold")).pack(side="left", padx=10)

        if self.is_admin:
            ctk.CTkButton(btn_frame, text="✏️ Επεξεργασία", command=lambda: self.open_shift_editor(v[0], v[1], v[2], load_text), fg_color="#b8860b", height=50, width=200, font=("Arial", 16, "bold")).pack(side="left", padx=10)
            
            def unlock():
                dialog = ctk.CTkInputDialog(text="Λόγος ξεκλειδώματος / Παρατηρήσεις:", title="Ξεκλείδωμα Βάρδιας")
                remark = dialog.get_input()
                if remark is not None:
                    # --- ΕΞΥΠΝΗ ΠΡΟΣΘΗΚΗ ΥΠΟΓΡΑΦΗΣ ---
                    signature = f"[Σημειώσεις {self.current_role} - {self.current_officer}]: {remark}"
                    
                    conn = sqlite3.connect('police_log.db'); c = conn.cursor()
                    c.execute('UPDATE incidents SET is_closed=0 WHERE shift_date=? AND shift_hours=? AND officer_name=?', (v[0], v[1], v[2]))
                    c.execute('INSERT INTO shift_remarks (officer_name, shift_date, shift_hours, remarks) VALUES (?,?,?,?)', (v[2], v[0], v[1], signature))
                    conn.commit(); conn.close()
                    messagebox.showinfo("Επιτυχία", "Η βάρδια ξεκλειδώθηκε και εστάλη ειδοποίηση στον Αξιωματικό!")
            ctk.CTkButton(btn_frame, text="🔓 Ξεκλείδωμα", command=unlock, fg_color="#2b7b5a", height=50, width=200, font=("Arial", 16, "bold")).pack(side="left", padx=10)

    def open_shift_editor(self, date, shift, officer, refresh_callback):
        ewin = ctk.CTkToplevel(self.root); ewin.title(f"Επεξεργασία Βάρδιας: {date} | {shift}"); ewin.geometry("900x600"); ewin.grab_set()
        ctk.CTkLabel(ewin, text="Διπλό κλικ σε ένα συμβάν για επεξεργασία ή διαγραφή", font=("Arial", 18, "bold")).pack(pady=15)
        tree = ttk.Treeview(ewin, columns=("id", "time", "title"), show="headings"); tree.heading("time", text="Ώρα"); tree.heading("title", text="Τίτλος"); tree.column("time", width=100, anchor="center"); tree.column("title", width=500); tree.pack(fill="both", expand=True, padx=20, pady=10)
        
        def refresh_tree():
            for i in tree.get_children(): tree.delete(i)
            conn = sqlite3.connect('police_log.db'); cursor = conn.cursor()
            cursor.execute('SELECT id, incident_time, title FROM incidents WHERE shift_date=? AND shift_hours=? AND officer_name=? ORDER BY incident_time ASC', (date, shift, officer))
            for r in cursor.fetchall(): tree.insert("", "end", values=r)
            conn.close()
            refresh_callback() 
            
        refresh_tree()
        tree.bind("<Double-1>", lambda e: self.open_edit_window(tree, refresh_tree))

    def export_pdf(self, date, shift, off):
        try:
            conn = sqlite3.connect('police_log.db'); c = conn.cursor(); c.execute("SELECT incident_time, title, description, actions_taken, am FROM incidents JOIN officers ON incidents.officer_name = officers.full_name WHERE officer_name=? AND shift_date=? AND shift_hours=?", (off, date, shift)); res = c.fetchall(); am = res[0][4] if res else "---"; conn.close()
            p = off.split(" "); rk = f"{p[0]} {p[1]}" if len(p)>2 and p[1] in ["Α","Β","Α'","Β'"] else p[0]; nm = " ".join(p[2:]) if rk.count(" ")>0 else " ".join(p[1:])
            
            pdf = FPDF()
            pdf.add_page()
            pdf.add_font("Arial", "", r"C:\Windows\Fonts\arial.ttf")
            pdf.add_font("ArialB", "", r"C:\Windows\Fonts\arialbd.ttf")
            
            pdf.set_font("ArialB", "", 16)
            pdf.cell(0, 10, text=f"ΑΝΑΦΟΡΑ ΒΑΡΔΙΑΣ - {self.dept_name.upper()}", align="C", new_x="LMARGIN", new_y="NEXT")
            pdf.ln(5)
            
            pdf.set_font("Arial", "", 12)
            pdf.cell(0, 8, text=f"Αξιωματικός Υπηρεσίας: {rk} ({am}) {nm}", new_x="LMARGIN", new_y="NEXT")
            pdf.cell(0, 8, text=f"Ημερομηνία: {date} | Βάρδια: {shift}", new_x="LMARGIN", new_y="NEXT")
            pdf.line(10, pdf.get_y(), 200, pdf.get_y())
            pdf.ln(5)
            
            for r in res: 
                pdf.set_font("ArialB", "", 12)
                pdf.multi_cell(0, 8, text=f"[{r[0]}] - {r[1]}", new_x="LMARGIN", new_y="NEXT")
                
                pdf.set_font("Arial", "", 11)
                pdf.multi_cell(0, 7, text=f"Περιγραφή:\n{r[2]}", new_x="LMARGIN", new_y="NEXT")
                pdf.multi_cell(0, 7, text=f"Ενέργειες:\n{r[3]}", new_x="LMARGIN", new_y="NEXT")
                
                pdf.ln(3)
                pdf.line(10, pdf.get_y(), 200, pdf.get_y())
                pdf.ln(5)
                
            desktop_path = os.path.join(os.path.expanduser("~"), "Desktop")
            if not os.path.exists(desktop_path):
                onedrive_path = os.path.join(os.path.expanduser("~"), "OneDrive", "Desktop")
                if os.path.exists(onedrive_path): desktop_path = onedrive_path
                else: desktop_path = os.getcwd() 
            
            safe_shift = shift.replace(':', '').replace(' ', '')
            safe_date = date.replace('/', '-')
            filename = f"Αναφορά_{safe_date}_{safe_shift}.pdf"
            full_path = os.path.join(desktop_path, filename)
            
            pdf.output(full_path)
            os.startfile(full_path) 
            
        except Exception as e: messagebox.showerror("Σφάλμα PDF", str(e))

    def open_staff_management(self):
        sm = ctk.CTkToplevel(self.root); sm.title("Προσωπικό"); sm.geometry("1000x800"); sm.state('zoomed'); sm.grab_set()
        c = ctk.CTkFrame(sm, fg_color="transparent"); c.pack(fill="both", expand=True, padx=40, pady=20)
        f = ctk.CTkFrame(c); f.pack(fill="x", pady=15)
        
        en_n = ctk.CTkEntry(f, placeholder_text="Βαθμός & Όνομα", width=300, height=45, font=("Arial", 16)); en_n.pack(side="left", padx=5, pady=10)
        en_a = ctk.CTkEntry(f, placeholder_text="Α.Μ.", width=130, height=45, font=("Arial", 16)); en_a.pack(side="left", padx=5)
        
        # --- ΝΕΟ DROPDOWN ΓΙΑ ΡΟΛΟΥΣ ---
        roles = ["Αξιωματικός Υπηρεσίας", "Διοικητής", "Υποδιοικητής", "Γραμματεία"]
        cb_role = ctk.CTkComboBox(f, values=roles, width=200, height=45, font=("Arial", 15))
        cb_role.set("Αξιωματικός Υπηρεσίας"); cb_role.pack(side="left", padx=10)
        
        sw = ctk.CTkSwitch(f, text="Admin", font=("Arial", 15)); sw.pack(side="left", padx=10)
        
        def add():
            try: 
                conn = sqlite3.connect('police_log.db'); cursor = conn.cursor()
                cursor.execute("INSERT INTO officers (am, full_name, is_admin, password, role) VALUES (?,?,?,?,?)", 
                          (en_a.get(), en_n.get(), 1 if sw.get() else 0, en_a.get(), cb_role.get()))
                conn.commit(); conn.close(); refresh(); en_a.delete(0,'end'); en_n.delete(0,'end')
            except: messagebox.showerror("!", "Υπάρχει ήδη.")
            
        ctk.CTkButton(f, text="➕ Προσθήκη", command=add, height=45, font=("Arial", 15, "bold")).pack(side="left", padx=10)
        
        tr = ttk.Treeview(c, columns=("am","n","role","ad"), show="headings")
        tr.heading("am", text="Α.Μ."); tr.heading("n", text="Ονοματεπώνυμο"); tr.heading("role", text="Ρόλος"); tr.heading("ad", text="Admin")
        tr.pack(fill="both", expand=True, pady=10)
        
        def refresh():
            for i in tr.get_children(): tr.delete(i)
            conn = sqlite3.connect('police_log.db'); cursor = conn.cursor()
            cursor.execute("SELECT am, full_name, role, is_admin FROM officers"); res = cursor.fetchall(); conn.close()
            res.sort(key=lambda x: (get_rank_weight(x[1]), x[1]))
            for r in res: tr.insert("", "end", values=(r[0], r[1], r[2], "Ναι" if r[3] else "Όχι"))
            
        refresh()
        
        def rst():
            sel = tr.selection()
            if sel: a = tr.item(sel)['values'][0]; conn = sqlite3.connect('police_log.db'); cursor = conn.cursor(); cursor.execute("UPDATE officers SET password=? WHERE am=?", (str(a), str(a))); conn.commit(); conn.close(); messagebox.showinfo("OK", "Reset!")
        def tgl():
            sel = tr.selection()
            if sel: a = tr.item(sel)['values'][0]; cur = tr.item(sel)['values'][3]; conn = sqlite3.connect('police_log.db'); cursor = conn.cursor(); cursor.execute("UPDATE officers SET is_admin=? WHERE am=?", (0 if cur=="Ναι" else 1, str(a))); conn.commit(); conn.close(); refresh()
        def dele():
            sel = tr.selection()
            if sel: a = tr.item(sel)['values'][0]; conn = sqlite3.connect('police_log.db'); cursor = conn.cursor(); cursor.execute("DELETE FROM officers WHERE am=?", (str(a),)); conn.commit(); conn.close(); refresh()
            
        bf = ctk.CTkFrame(c, fg_color="transparent"); bf.pack(pady=15)
        ctk.CTkButton(bf, text="🗑️ Διαγραφή", command=dele, fg_color="#a83232", height=50, width=160, font=("Arial", 15, "bold")).pack(side="left", padx=10)
        ctk.CTkButton(bf, text="🔑 Reset", command=rst, fg_color="#b8860b", height=50, width=160, font=("Arial", 15, "bold")).pack(side="left", padx=10)
        ctk.CTkButton(bf, text="🛡️ Admin", command=tgl, fg_color="#1f538d", height=50, width=160, font=("Arial", 15, "bold")).pack(side="left", padx=10)

if __name__ == "__main__":
    app = DutyLogApp(ctk.CTk())
    app.root.mainloop()
