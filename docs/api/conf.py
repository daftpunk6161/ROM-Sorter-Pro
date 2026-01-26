import os
import sys

project = "ROM-Sorter-Pro API"

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if ROOT not in sys.path:
	sys.path.insert(0, ROOT)
extensions = ["sphinx.ext.autodoc", "sphinx.ext.napoleon"]
master_doc = "index"
exclude_patterns = []
