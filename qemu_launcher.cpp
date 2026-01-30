#include <iostream>
#include <vector>
#include <string>
#include <process.h>

int main(int argc, char* argv[]) {
    if (argc < 12) return 1;

    // On construit la commande pour Windows
    std::string cmd = "qemu-system-x86_64.exe";

    std::vector<std::string> args;
    args.push_back("-accel"); args.push_back("whpx"); // Accélération Windows (Hyper-V)
    args.push_back("-m"); args.push_back(argv[2]);
    args.push_back("-smp"); args.push_back(argv[3]);

    std::string drive = "file=" + std::string(argv[1]) + ",format=qcow2";
    args.push_back("-drive"); args.push_back(drive);

    if (std::string(argv[4]) != "None") {
        args.push_back("-cdrom"); args.push_back(argv[4]);
    }

    // Graphismes 3D (ANGLE pour Windows)
    args.push_back("-vga"); args.push_back("virtio");
    args.push_back("-display"); args.push_back("gtk,zoom-to-fit=on");

    args.push_back("-netdev"); args.push_back("user,id=net0");
    args.push_back("-device"); args.push_back(std::string(argv[9]) + ",netdev=net0");

    if (std::string(argv[11]) == "1") {
        args.push_back("-device"); args.push_back("qemu-xhci");
    }

    // Pour l'UEFI sur Windows, le chemin dépend de ton installation
    if (std::string(argv[5]) == "1") {
        args.push_back("-bios"); args.push_back("OVMF.fd");
    }

    // Construction de l'appel système
    std::string full_cmd = cmd;
    for (const auto& arg : args) full_cmd += " " + arg;

    return system(full_cmd.c_str());
}
