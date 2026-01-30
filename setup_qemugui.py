import os
import sys
import subprocess
import shutil

def install_dependencies():
    print("--- Installation des dépendances Python ---")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "PyQt6", "pyinstaller"])

def compile_cpp():
    print("--- Compilation du moteur C++ ---")
    # Vérifie si G++ est présent (MinGW)
    if shutil.which("g++"):
        subprocess.run(["g++", "qemu_launcher.cpp", "-o", "qemu_launcher.exe", "-static"], shell=True)
    else:
        print("Erreur: g++ non trouvé. Installez MinGW ou passez par MSVC.")

def build_exe():
    print("--- Création du package EXE final ---")
    # On utilise PyInstaller pour l'interface
    # --add-data inclut le moteur compilé et l'icône dans l'EXE
    cmd = [
        "pyinstaller",
        "--noconfirm",
        "--onefile",
        "--windowed",
        "--icon=qemugui.png",
        "--add-data", "qemu_launcher.exe;.",
        "--add-data", "qemugui.png;.",
        "--name", "qemugui",
        "qemugui.py"
    ]
    subprocess.run(cmd, shell=True)

if __name__ == "__main__":
    install_dependencies()
    compile_cpp()
    build_exe()
    print("\nTerminé ! Votre application se trouve dans le dossier 'dist/qemugui.exe'")
