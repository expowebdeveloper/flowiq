import sys
import os
import importlib

# 1. Save original sys.path
original_path = list(sys.path)

# 2. Exclude current directory, parent directory, and any 'backend' path to prevent loading ourselves
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path = [
    p for p in sys.path 
    if p not in ('', '.') and os.path.abspath(p) not in (os.path.abspath(current_dir), os.path.abspath(parent_dir))
]

# 3. Temporarily remove 'json' from sys.modules to force loading from the system library paths
sys.modules.pop('json', None)

# 4. Import the real system library json module
real_json = importlib.import_module('json')

# 5. Restore original sys.path
sys.path = original_path

# 6. Put the real json module back into sys.modules so subsequent imports get it directly
sys.modules['json'] = real_json

# 7. Copy all standard json attributes to this package's namespace
# so the current import resolves standard functions (loads, dumps, JSONDecodeError, etc.)
globals().update(real_json.__dict__)
