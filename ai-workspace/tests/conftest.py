"""Global test configuration - adds backend to Python path."""

import sys
import os
from pathlib import Path

# Add the backend directory to Python path
backend_dir = Path(__file__).parent.parent / "apps" / "backend"
sys.path.insert(0, str(backend_dir.resolve()))

# Also add the project root
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root.resolve()))
