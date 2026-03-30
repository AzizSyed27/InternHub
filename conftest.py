# conftest.py — root-level pytest configuration
# Ensures tracker/ and networking/ are both on sys.path so their test
# packages resolve independently even though both are named "tests".

import sys
from pathlib import Path

# Add the repo root to sys.path so `import tracker.x` and `import networking.x` work
sys.path.insert(0, str(Path(__file__).parent))
