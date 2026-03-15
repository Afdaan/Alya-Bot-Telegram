import sys
import os
from pathlib import Path

libs_path = str(Path(__file__).parent / "libs")
if libs_path not in sys.path:
    sys.path.insert(0, libs_path)

print(f"DEBUG: sys.path[0] = {sys.path[0]}")

try:
    import rvc_python
    print(f"DEBUG: rvc_python file = {rvc_python.__file__}")
    
    from rvc_python.infer import RVCInference
    print("DEBUG: Successfully imported RVCInference")
    
    import rvc_python.lib
    print("DEBUG: Successfully imported rvc_python.lib")
except Exception as e:
    print(f"DEBUG: Error = {e}")
    import traceback
    traceback.print_exc()
