import sys, subprocess, os, sqlite3, struct
from PyQt6.QtWidgets import *
from PyQt6.QtGui import QIcon
from PyQt6.QtCore import Qt

# --- GESTION DES CHEMINS (PyInstaller & Windows) ---
def resource_path(relative_path):
    """ Trouve le chemin du fichier, que ce soit en script ou en EXE """
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

# Détection de l'exécutable QEMU
def get_qemu_path(exe_name="qemu-system-x86_64.exe"):
    """ Cherche QEMU dans le dossier par défaut ou dans le PATH """
    default_path = os.path.join(r"C:\Program Files\qemu", exe_name)
    if os.path.exists(default_path):
        return default_path
    return exe_name # Repli sur le PATH si non trouvé dans Program Files

class QemuStation(QWidget):
    def __init__(self):
        super().__init__()
        # Stockage de la DB dans AppData
        appdata = os.environ.get('APPDATA', os.path.expanduser("~"))
        self.db_path = os.path.join(appdata, "qemugui.db")
        
        self.init_db()
        self.qcow2_path = ""
        self.iso_path = ""
        self.initUI()
        self.load_library()

    def init_db(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''CREATE TABLE IF NOT EXISTS vms
            (id INTEGER PRIMARY KEY, name TEXT, qcow2 TEXT, iso TEXT, ram INTEGER, cpu INTEGER, uefi INTEGER)''')
        conn.commit()
        conn.close()

    def initUI(self):
        self.setWindowTitle('qemugui - Edition Intégrale')
        self.setMinimumSize(1150, 850)
        
        # Icône pour la barre de titre
        icon_path = resource_path("qemugui.png")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
        
        self.setStyleSheet("""
            QWidget { background-color: #1e1e1e; color: #efefef; font-family: 'Segoe UI', sans-serif; }
            QFrame#Sidebar { background-color: #252526; border-right: 1px solid #333; }
            
            QGroupBox { 
                font-weight: bold; border: 2px solid #3d3d3d; border-radius: 12px; 
                margin-top: 25px; padding-top: 25px; 
            }
            QGroupBox::title { 
                subcontrol-origin: margin; left: 20px; padding: 5px 15px; 
                color: white; font-size: 18px; background-color: #1e1e1e; 
            }
            
            QLabel#ParamLabel { color: #007aff; font-weight: bold; }
            
            QPushButton { background-color: #333; border-radius: 6px; padding: 10px; border: 1px solid #444; }
            QPushButton:hover { background-color: #444; }
            QPushButton#RunBtn { background-color: #28a745; color: white; font-weight: bold; font-size: 16px; border: none; }
            
            QLineEdit, QSpinBox, QComboBox { background-color: #2d2d2d; border: 1px solid #3d3d3d; border-radius: 5px; padding: 8px; }
            QListWidget::item:selected { background-color: #007aff; color: white; }
            QScrollArea { border: none; }
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # --- SIDEBAR ---
        sidebar = QFrame(); sidebar.setObjectName("Sidebar")
        side_lay = QVBoxLayout(sidebar)
        side_lay.setContentsMargins(15, 30, 15, 15)
        side_lay.addWidget(QLabel("<b>BIBLIOTHÈQUE</b>"))
        self.vm_list = QListWidget()
        self.vm_list.itemClicked.connect(self.load_selected_vm)
        side_lay.addWidget(self.vm_list)
        btn_del = QPushButton("Supprimer VM"); btn_del.clicked.connect(self.delete_vm)
        side_lay.addWidget(btn_del)
        layout.addWidget(sidebar, 1)

        # --- CONTENU PRINCIPAL ---
        content = QFrame()
        content_lay = QVBoxLayout(content)
        content_lay.setContentsMargins(40, 20, 40, 30)
        self.in_name = QLineEdit(); self.in_name.setPlaceholderText("Nom de la machine virtuelle...")
        content_lay.addWidget(self.in_name)

        scroll = QScrollArea(); scroll.setWidgetResizable(True)
        scroll_content = QWidget(); scroll_lay = QVBoxLayout(scroll_content)
        scroll_lay.setSpacing(20)
        
        # 1. STOCKAGE
        group_storage = QGroupBox("STOCKAGE")
        gl = QVBoxLayout(); gl.setContentsMargins(15, 25, 15, 15)
        h_btns = QHBoxLayout()
        btn_d = QPushButton("Choisir Disque..."); btn_d.clicked.connect(self.select_qcow2)
        btn_new = QPushButton("CRÉER DISQUE (Gb)"); btn_new.setStyleSheet("color: #007aff; font-weight: bold;")
        btn_new.clicked.connect(self.gui_create_disk)
        btn_i = QPushButton("Charger ISO..."); btn_i.clicked.connect(self.select_iso)
        h_btns.addWidget(btn_d); h_btns.addWidget(btn_new); h_btns.addWidget(btn_i)
        gl.addLayout(h_btns)
        self.label_info = QLabel("Fichier: Aucun"); self.label_info.setObjectName("ParamLabel")
        gl.addWidget(self.label_info)
        group_storage.setLayout(gl); scroll_lay.addWidget(group_storage)

        # 2. PROCESSEUR
        group_hw = QGroupBox("PROCESSEUR")
        hl = QHBoxLayout(); hl.setContentsMargins(15, 25, 15, 15)
        self.ram_in = QSpinBox(); self.ram_in.setRange(512, 64000); self.ram_in.setValue(4096)
        self.cpu_in = QSpinBox(); self.cpu_in.setRange(1, 16); self.cpu_in.setValue(4)
        hl.addWidget(QLabel("RAM:")); hl.addWidget(self.ram_in); hl.addWidget(QLabel("CPU:")); hl.addWidget(self.cpu_in)
        group_hw.setLayout(hl); scroll_lay.addWidget(group_hw)

        # 3. PÉRIPHÉRIQUES
        group_ext = QGroupBox("PÉRIPHÉRIQUES")
        el = QGridLayout(); el.setContentsMargins(15, 25, 15, 15)
        self.combo_net = QComboBox(); self.combo_net.addItems(["virtio-net-pci", "e1000"])
        el.addWidget(QLabel("RÉSEAU:"), 0, 0); el.addWidget(self.combo_net, 0, 1)
        self.check_usb = QCheckBox("USB 3.0"); el.addWidget(self.check_usb, 1, 0)
        group_ext.setLayout(el); scroll_lay.addWidget(group_ext)

        # 4. AFFICHAGE
        group_boot = QGroupBox("AFFICHAGE")
        bl = QHBoxLayout(); bl.setContentsMargins(15, 25, 15, 15)
        self.combo_vram = QComboBox(); self.combo_vram.addItems(["128", "256", "512"])
        self.check_uefi = QCheckBox("UEFI")
        bl.addWidget(QLabel("VRAM:")); bl.addWidget(self.combo_vram); bl.addWidget(self.check_uefi)
        group_boot.setLayout(bl); scroll_lay.addWidget(group_boot)

        scroll.setWidget(scroll_content); content_lay.addWidget(scroll)
        
        # PIED DE PAGE
        footer = QHBoxLayout()
        btn_save = QPushButton("Enregistrer la VM"); btn_save.clicked.connect(self.save_vm)
        self.btn_run = QPushButton("▶ DÉMARRER LA SESSION"); self.btn_run.setObjectName("RunBtn")
        self.btn_run.setFixedHeight(65); self.btn_run.clicked.connect(self.run_vm)
        footer.addWidget(btn_save); footer.addWidget(self.btn_run)
        content_lay.addLayout(footer)
        layout.addWidget(content, 3)

    # --- LOGIQUE ---

    def gui_create_disk(self):
        path, _ = QFileDialog.getSaveFileName(self, "Créer un disque QCOW2", "", "QEMU Disk (*.qcow2)")
        if not path: return
        if not path.endswith(".qcow2"): path += ".qcow2"
        
        size_gb, ok = QInputDialog.getInt(self, "Taille du disque", "Capacité en Go :", 20, 1, 2000)
        if ok:
            try:
                # Utilisation de qemu-img.exe (détection automatique)
                qemu_img = get_qemu_path("qemu-img.exe")
                subprocess.run([qemu_img, "create", "-f", "qcow2", path, f"{size_gb}G"], check=True)
                QMessageBox.information(self, "Succès", f"Disque de {size_gb} Go créé !")
                self.qcow2_path = path
                self.label_info.setText(f"Fichier: {os.path.basename(path)}")
            except Exception as e:
                QMessageBox.critical(self, "Erreur", f"Échec de création du disque.\nVérifiez l'installation de QEMU.\n{e}")

    def select_qcow2(self):
        f, _ = QFileDialog.getOpenFileName(self, "Choisir Disque", "", "Images (*.qcow2 *.img)")
        if f: self.qcow2_path = f; self.label_info.setText(f"Fichier: {os.path.basename(f)}")

    def select_iso(self):
        f, _ = QFileDialog.getOpenFileName(self, "Choisir ISO", "", "ISO (*.iso)")
        if f: self.iso_path = f

    def save_vm(self):
        if not self.in_name.text(): return
        conn = sqlite3.connect(self.db_path); cursor = conn.cursor()
        cursor.execute("INSERT OR REPLACE INTO vms (name, qcow2, iso, ram, cpu, uefi) VALUES (?, ?, ?, ?, ?, ?)",
                       (self.in_name.text(), self.qcow2_path, self.iso_path, self.ram_in.value(), self.cpu_in.value(), 1 if self.check_uefi.isChecked() else 0))
        conn.commit(); conn.close(); self.load_library()

    def load_library(self):
        self.vm_list.clear()
        conn = sqlite3.connect(self.db_path); cursor = conn.cursor()
        cursor.execute("SELECT name FROM vms"); [self.vm_list.addItem(r[0]) for r in cursor.fetchall()]; conn.close()

    def load_selected_vm(self, item):
        conn = sqlite3.connect(self.db_path); cursor = conn.cursor()
        cursor.execute("SELECT * FROM vms WHERE name=?", (item.text(),)); v = cursor.fetchone(); conn.close()
        if v: 
            self.in_name.setText(v[1]); self.qcow2_path = v[2]; self.iso_path = v[3]
            self.ram_in.setValue(v[4]); self.cpu_in.setValue(v[5]); self.check_uefi.setChecked(v[6] == 1)
            self.label_info.setText(f"Fichier: {os.path.basename(v[2])}" if v[2] else "Fichier: Aucun")

    def delete_vm(self):
        if self.vm_list.currentItem():
            conn = sqlite3.connect(self.db_path); cursor = conn.cursor()
            cursor.execute("DELETE FROM vms WHERE name=?", (self.vm_list.currentItem().text(),))
            conn.commit(); conn.close(); self.load_library()

    def run_vm(self):
        if not self.qcow2_path:
            QMessageBox.warning(self, "Attention", "Veuillez sélectionner un disque dur.")
            return
            
        qemu_bin = get_qemu_path("qemu-system-x86_64.exe")
        
        cmd = [
            qemu_bin, 
            "-accel", "whpx", 
            "-m", str(self.ram_in.value()), 
            "-smp", str(self.cpu_in.value()), 
            "-drive", f"file={self.qcow2_path},format=qcow2", 
            "-vga", "virtio", 
            "-display", "gtk,zoom-to-fit=on"
        ]
        
        if self.iso_path:
            cmd += ["-cdrom", self.iso_path]
            
        try:
            subprocess.Popen(cmd)
        except Exception as e:
            QMessageBox.critical(self, "Erreur Critique", f"Impossible de lancer QEMU.\nChemin utilisé : {qemu_bin}\n\nErreur : {e}")

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = QemuStation()
    ex.show()
    sys.exit(app.exec())
