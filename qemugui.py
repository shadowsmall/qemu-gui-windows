#!/usr/bin/env python3
import sys, subprocess, os, sqlite3
from PyQt6.QtWidgets import *
from PyQt6.QtGui import QIcon, QFont
from PyQt6.QtCore import Qt

# --- GESTION DES CHEMINS POUR L'EXE (PyInstaller) ---
def resource_path(relative_path):
    """ Trouve le chemin du fichier, que ce soit en script ou en EXE """
    try:
        # Chemin temporaire créé par PyInstaller
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

class QemuStation(QWidget):
    def __init__(self):
        super().__init__()
        # Stockage de la DB dans AppData pour Windows
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
            (id INTEGER PRIMARY KEY, name TEXT, qcow2 TEXT, iso TEXT,
             ram INTEGER, cpu INTEGER, uefi INTEGER, kbd TEXT)''')
        conn.commit()
        conn.close()

    def initUI(self):
        self.setWindowTitle('qemugui - Windows Pro')
        self.setMinimumSize(1150, 850)

        # Chargement de l'icône via resource_path
        icon_file = resource_path("qemugui.png")
        if os.path.exists(icon_file):
            self.setWindowIcon(QIcon(icon_file))

        # --- STYLE GRAPHIQUE ---
        self.setStyleSheet("""
            QWidget { background-color: #1e1e1e; color: #efefef; font-family: 'Segoe UI', sans-serif; }
            QFrame#Sidebar { background-color: #252526; border-right: 1px solid #333; }

            /* TITRES DE SECTION (BLANC) */
            QGroupBox {
                font-weight: bold; border: 2px solid #3d3d3d; border-radius: 12px;
                margin-top: 35px; padding-top: 25px;
            }
            QGroupBox::title {
                subcontrol-origin: margin; subcontrol-position: top left;
                left: 20px; padding: 5px 15px; color: white;
                font-size: 18px; font-weight: bold; background-color: #1e1e1e;
            }

            /* LABELS DES PARAMETRES (BLEU) */
            QLabel#ParamLabel { color: #007aff; font-weight: bold; font-size: 13px; }

            QPushButton { background-color: #333; border-radius: 6px; padding: 10px; border: 1px solid #444; }
            QPushButton:hover { background-color: #444; }
            QPushButton#RunBtn { background-color: #28a745; color: white; font-weight: bold; font-size: 16px; border: none; }

            QLineEdit, QSpinBox, QComboBox { background-color: #2d2d2d; border: 1px solid #3d3d3d; border-radius: 5px; padding: 8px; }

            QListWidget { background-color: transparent; border: none; }
            QListWidget::item { padding: 15px; border-radius: 8px; margin-bottom: 5px; }
            QListWidget::item:selected { background-color: #007aff; color: white; }

            QScrollArea { border: none; }
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # --- SIDEBAR ---
        sidebar = QFrame(); sidebar.setObjectName("Sidebar")
        side_lay = QVBoxLayout(sidebar)
        side_lay.setContentsMargins(15, 30, 15, 15)
        side_lay.addWidget(QLabel("<b style='font-size: 15px;'>BIBLIOTHÈQUE</b>"))

        self.vm_list = QListWidget()
        self.vm_list.itemClicked.connect(self.load_selected_vm)
        side_lay.addWidget(self.vm_list)

        btn_del = QPushButton("Supprimer VM"); btn_del.clicked.connect(self.delete_vm)
        side_lay.addWidget(btn_del)
        layout.addWidget(sidebar, 1)

        # --- CONTENU PRINCIPAL ---
        content = QFrame()
        content_lay = QVBoxLayout(content)
        content_lay.setContentsMargins(40, 30, 40, 30)

        self.in_name = QLineEdit(); self.in_name.setPlaceholderText("Nom de la machine virtuelle...")
        self.in_name.setFixedHeight(45)
        content_lay.addWidget(self.in_name)

        scroll = QScrollArea(); scroll.setWidgetResizable(True)
        scroll_content = QWidget(); scroll_lay = QVBoxLayout(scroll_content)
        scroll_lay.setSpacing(25)

        # 1. STOCKAGE
        group_storage = QGroupBox("STOCKAGE")
        gl = QVBoxLayout()
        gl.setContentsMargins(15, 25, 15, 15)
        h1 = QHBoxLayout()
        btn_disk = QPushButton("Choisir Disque Dur (.qcow2)"); btn_disk.clicked.connect(self.select_qcow2)
        btn_iso = QPushButton("Charger Fichier ISO"); btn_iso.clicked.connect(self.select_iso)
        h1.addWidget(btn_disk); h1.addWidget(btn_iso)
        gl.addLayout(h1)
        self.label_info = QLabel("Fichier: Aucun"); self.label_info.setObjectName("ParamLabel")
        gl.addWidget(self.label_info)
        group_storage.setLayout(gl); scroll_lay.addWidget(group_storage)

        # 2. PROCESSEUR
        group_hw = QGroupBox("PROCESSEUR")
        hl = QHBoxLayout()
        hl.setContentsMargins(15, 25, 15, 15)
        lbl_ram = QLabel("RAM (Mo):"); lbl_ram.setObjectName("ParamLabel")
        lbl_cpu = QLabel("COEURS CPU:"); lbl_cpu.setObjectName("ParamLabel")
        self.ram_in = QSpinBox(); self.ram_in.setRange(512, 128000); self.ram_in.setValue(4096)
        self.cpu_in = QSpinBox(); self.cpu_in.setRange(1, 32); self.cpu_in.setValue(4)
        hl.addWidget(lbl_ram); hl.addWidget(self.ram_in); hl.addSpacing(20); hl.addWidget(lbl_cpu); hl.addWidget(self.cpu_in)
        group_hw.setLayout(hl); scroll_lay.addWidget(group_hw)

        # 3. PÉRIPHÉRIQUES
        group_ext = QGroupBox("PÉRIPHÉRIQUES")
        el = QGridLayout()
        el.setContentsMargins(15, 25, 15, 15)
        lbl_net = QLabel("RÉSEAU:"); lbl_net.setObjectName("ParamLabel")
        lbl_son = QLabel("CARTE SON:"); lbl_son.setObjectName("ParamLabel")
        el.addWidget(lbl_net, 0, 0); self.combo_net = QComboBox(); self.combo_net.addItems(["virtio-net-pci", "e1000"])
        el.addWidget(self.combo_net, 0, 1)
        el.addWidget(lbl_son, 0, 2); self.combo_audio = QComboBox(); self.combo_audio.addItems(["duplex", "output"])
        el.addWidget(self.combo_audio, 0, 3)
        self.check_usb = QCheckBox("Activer USB 3.0 (XHCI)"); self.check_usb.setStyleSheet("color: #007aff; font-weight: bold;")
        el.addWidget(self.check_usb, 1, 0, 1, 2)
        group_ext.setLayout(el); scroll_lay.addWidget(group_ext)

        # 4. AFFICHAGE
        group_boot = QGroupBox("AFFICHAGE")
        bl = QHBoxLayout()
        bl.setContentsMargins(15, 25, 15, 15)
        lbl_vram = QLabel("VRAM (Mo):"); lbl_vram.setObjectName("ParamLabel")
        self.combo_vram = QComboBox(); self.combo_vram.addItems(["128", "256", "512", "1024", "2048"])
        self.check_uefi = QCheckBox("Mode UEFI"); self.check_sboot = QCheckBox("Secure Boot")
        bl.addWidget(lbl_vram); bl.addWidget(self.combo_vram); bl.addSpacing(20); bl.addWidget(self.check_uefi); bl.addWidget(self.check_sboot)
        group_boot.setLayout(bl); scroll_lay.addWidget(group_boot)

        scroll.setWidget(scroll_content)
        content_lay.addWidget(scroll)

        # PIED DE PAGE
        footer = QHBoxLayout()
        btn_save = QPushButton("Enregistrer la Config"); btn_save.clicked.connect(self.save_vm)
        self.btn_run = QPushButton("▶ DÉMARRER LA VM"); self.btn_run.setObjectName("RunBtn")
        self.btn_run.setFixedHeight(65); self.btn_run.clicked.connect(self.run_vm)
        footer.addWidget(btn_save); footer.addWidget(self.btn_run)
        content_lay.addLayout(footer)

        layout.addWidget(content, 3)
        self.setLayout(layout)

    # --- FONCTIONS ---
    def select_qcow2(self):
        f, _ = QFileDialog.getOpenFileName(self, "Choisir Disque", "", "Images (*.qcow2 *.img)")
        if f: self.qcow2_path = f; self.label_info.setText(f"Fichier: {os.path.basename(f)}")

    def select_iso(self):
        f, _ = QFileDialog.getOpenFileName(self, "Choisir ISO", "", "ISO (*.iso)")
        if f: self.iso_path = f

    def save_vm(self):
        if not self.in_name.text():
            QMessageBox.warning(self, "Erreur", "Veuillez donner un nom à la VM.")
            return
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("INSERT OR REPLACE INTO vms (name, qcow2, iso, ram, cpu, uefi, kbd) VALUES (?, ?, ?, ?, ?, ?, ?)",
                       (self.in_name.text(), self.qcow2_path, self.iso_path, self.ram_in.value(),
                        self.cpu_in.value(), 1 if self.check_uefi.isChecked() else 0, "fr"))
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
            QMessageBox.critical(self, "Erreur", "Aucun disque dur sélectionné !")
            return

        launcher_exe = resource_path("qemu_launcher.exe")

        # Arguments pour le lanceur C++
        cmd = [
            launcher_exe,
            self.qcow2_path,
            str(self.ram_in.value()),
            str(self.cpu_in.value()),
            self.iso_path if self.iso_path else "None",
            "1" if self.check_uefi.isChecked() else "0",
            "fr",
            self.combo_vram.currentText(),
            "0",
            self.combo_net.currentText(),
            self.combo_audio.currentText(),
            "1" if self.check_usb.isChecked() else "0"
        ]

        try:
            subprocess.Popen(cmd)
        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Impossible de lancer QEMU: {e}")

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = QemuStation()
    ex.show()
    sys.exit(app.exec())
