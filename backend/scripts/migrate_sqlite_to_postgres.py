import os
import subprocess
from pathlib import Path
import tempfile

BASE_DIR = Path(__file__).resolve().parent.parent
MANAGE = BASE_DIR / "manage.py"

def dump_sqlite(dump_path):
    env = os.environ.copy()
    env["DB_ENGINE"] = "sqlite"
    subprocess.check_call(["python", str(MANAGE), "dumpdata", "--indent", "2", "-o", str(dump_path)], env=env)

def load_postgres(dump_path):
    env = os.environ.copy()
    env.update({
        "DB_ENGINE": "postgres",
        "POSTGRES_USER": env.get("POSTGRES_USER", "yelproot"),
        "POSTGRES_PASSWORD": env.get("POSTGRES_PASSWORD", "yelproot"),
        "POSTGRES_DB": env.get("POSTGRES_DB", "postgres"),
        "POSTGRES_HOST": env.get("POSTGRES_HOST", "localhost"),
        "POSTGRES_PORT": env.get("POSTGRES_PORT", "5432"),
    })
    subprocess.check_call(["python", str(MANAGE), "migrate"], env=env)
    subprocess.check_call(["python", str(MANAGE), "loaddata", str(dump_path)], env=env)

def main():
    with tempfile.TemporaryDirectory() as tmp:
        dump_file = Path(tmp) / "data.json"
        dump_sqlite(dump_file)
        load_postgres(dump_file)

if __name__ == "__main__":
    main()
