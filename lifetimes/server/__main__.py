"""Entry point: `python -m server`. Binds to HOST (default 127.0.0.1)."""
import os

import uvicorn

if __name__ == "__main__":
    uvicorn.run("server.main:app", host=os.environ.get("HOST", "127.0.0.1"),
                port=int(os.environ.get("PORT", "8000")), proxy_headers=False)
