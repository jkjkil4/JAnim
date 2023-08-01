import os
import platform
import subprocess as sp

def guarantee_existence(path: str) -> str:
    if not os.path.exists(path):
        os.makedirs(path)
    return os.path.abspath(path)

def open_file(filepath: str) -> None:
    current_os = platform.system()

    if current_os == "Windows":
        os.startfile(filepath)
    else:
        commands = []
        if current_os == "Linux":
            commands.append("xdg-open")
        elif current_os.startswith("CYGWIN"):
            commands.append("cygstart")
        else:  # Assume macOS
            commands.append("open")

        commands.append(filepath)

        FNULL = open(os.devnull, 'w')
        sp.call(commands, stdout=FNULL, stderr=sp.STDOUT)
        FNULL.close()
