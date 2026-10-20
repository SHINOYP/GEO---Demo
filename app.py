"""
Streamlit Cloud entrypoint.

Streamlit Cloud expects a root-level app.py. The actual application lives
in streamlit_app.py; this file just runs it, so there is a single source
of truth instead of two files that can silently drift out of sync.
"""
import os
import runpy

_HERE = os.path.dirname(os.path.abspath(__file__))
runpy.run_path(os.path.join(_HERE, "streamlit_app.py"), run_name="__main__")
