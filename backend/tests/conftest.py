import sys, pathlib

# Ensure app package and subpackages are resolvable whether PYTHONPATH is backend or backend/app
backend_dir = pathlib.Path(__file__).resolve().parent.parent
app_dir = backend_dir / "app"
if str(app_dir) not in sys.path:
    sys.path.insert(0, str(app_dir))
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))
