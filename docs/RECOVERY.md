# Recovery

The Git-backed source baseline is `origin/Shawn`. Save or copy uncommitted work first, then:

```bat
git fetch origin
git checkout Shawn
git reset --hard origin/Shawn
```

**Warning:** `git reset --hard` permanently discards tracked, uncommitted local changes. It does not restore ignored outputs, environments, model caches, or untracked files.

Recreate Python dependencies:

```bat
py -3.12 -m venv .venv312
.venv312\Scripts\activate
python -m pip install -r requirements.txt
```

Recreate frontend dependencies with `cd frontend` then `npm install`. Model weights live outside Git and must be restored/populated separately before offline use. Job outputs and local datasets are ignored; back them up independently. Run `python backend\tools\check_environment.py` after recovery.
