import sys
import os

# Ensure workspace root is always on sys.path for pytest runs
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
