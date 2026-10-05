import os
import tempfile
from pathlib import Path

# must run before app.config is imported: tests use a throwaway DB and no scheduler
os.environ["DATABASE_URL"] = f"sqlite:///{(Path(tempfile.mkdtemp()) / 'test.db').as_posix()}"
os.environ["ENABLE_SCHEDULER"] = "false"
