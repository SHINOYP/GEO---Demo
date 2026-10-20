import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BACKEND_DIR = os.path.join(REPO_ROOT, "citation-predictor", "backend")
for p in (REPO_ROOT, BACKEND_DIR):
    if p not in sys.path:
        sys.path.insert(0, p)
