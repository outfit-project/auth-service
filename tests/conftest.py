import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
for key, value in {
    "DB_NAME": "test", "DB_USER": "test", "DB_PASSWORD": "test",
    "SECRET_KEY": "unit-test-secret-with-more-than-thirty-two-characters",
    "CODE_PEPPER": "unit-test-pepper-with-more-than-sixteen-characters",
}.items():
    os.environ[key] = value
