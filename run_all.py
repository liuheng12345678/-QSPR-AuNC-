import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent

for script in ["predict_high_activity_structure.py", "predict_high_dispersity_structure.py"]:
    subprocess.check_call([sys.executable, str(ROOT / script)])

print("done")
