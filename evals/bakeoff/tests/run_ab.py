import pathlib, os
for ln in pathlib.Path('.env').read_text(encoding='utf-8').splitlines():
    ln = ln.strip()
    if ln and not ln.startswith('#') and '=' in ln:
        k, _, v = ln.partition('=')
        os.environ[k.strip()] = v.strip()
exec(open('evals/bakeoff/tests/scratch_stt_ab.py').read().replace(
    "REPO_ROOT = Path(__file__).resolve().parents[2]",
    "REPO_ROOT = pathlib.Path('.')"
).replace(
    "# Load .env manually before any imports that depend on env vars\n_env_path = REPO_ROOT / \".env\"\nif _env_path.exists():\n    for _line in _env_path.read_text(encoding=\"utf-8\").splitlines():\n        _line = _line.strip()\n        if _line and not _line.startswith(\"#\") and \"=\" in _line:\n            _k, _, _v = _line.partition(\"=\")\n            os.environ[_k.strip()] = _v.strip()\n",
    ""
))

