"""Entry point: `python -m app`. Binds to HOST (default 127.0.0.1)."""
import logging

import uvicorn

from .config import check_deployable, settings

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    check_deployable(settings)
    # Forwarded headers are not trusted: every absolute URL comes from APP_URL.
    uvicorn.run("app.web:app", host=settings.host, port=settings.port, proxy_headers=False)
