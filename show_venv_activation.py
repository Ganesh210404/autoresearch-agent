# show_venv_activation.py
# Prints the correct activation commands for a Python virtual environment named .venv.
#
# Usage examples:
#   python show_venv_activation.py
#   py show_venv_activation.py

commands = [
    r".\.venv\Scripts\Activate.ps1",   # Windows PowerShell
    r".venv\Scripts\activate.bat",      # Windows CMD
    r"source .venv/bin/activate",        # Bash (Linux/macOS)
]

for cmd in commands:
    print(cmd)