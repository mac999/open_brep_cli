import sys
from pathlib import Path

# Support running this file directly: `python src/main.py`.
if __package__ in (None, ""):
    project_root = str(Path(__file__).resolve().parents[1])
    if project_root not in sys.path:
        sys.path.insert(0, project_root)

from src.controller.repl import BRepCLI

def main():
    cli = BRepCLI()
    cli.cmdloop()

if __name__ == '__main__':
    main()
