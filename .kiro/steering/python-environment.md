# Python Environment

Always use the conda `test12` environment Python for all operations:

- Python binary: `/opt/homebrew/Caskroom/miniconda/base/envs/test12/bin/python`
- Pip: `/opt/homebrew/Caskroom/miniconda/base/envs/test12/bin/pip`
- All CLI tools (alembic, uvicorn, etc.) should be run via `/opt/homebrew/Caskroom/miniconda/base/envs/test12/bin/<tool>` or prefixed with `/opt/homebrew/Caskroom/miniconda/base/envs/test12/bin/python -m <module>`

Do NOT use the system Python (`/Users/csp/.local/bin/python`) — it is uv-managed and will reject package installs.
