import os
import sys
import subprocess

def run_as_admin():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    main_script = os.path.join(script_dir, "__main__.py")

    if sys.platform == 'win32':
        # Windows
        import ctypes
        if ctypes.windll.shell32.IsUserAnAdmin() == 0:
            print("Requesting admin privileges...")
            # Re-run with admin rights
            ctypes.windll.shell32.ShellExecuteW(
                None, "runas", sys.executable, f'"{main_script}"', script_dir, 1
            )
        else:
            # Already admin, run the script
            subprocess.run([sys.executable, main_script])
    else:
        # Linux/macOS
        if os.geteuid() != 0:
            print("Requesting admin privileges...")
            subprocess.run(['sudo', sys.executable, main_script])
        else:
            # Already admin, run the script
            subprocess.run([sys.executable, main_script])

if __name__ == "__main__":
    run_as_admin()