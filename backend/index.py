"""Vercel entrypoint.

Vercel's zero-configuration Flask preset looks for a WSGI ``app`` in
``app.py``, ``index.py``, ``server.py``, ``main.py``, ``wsgi.py`` or
``asgi.py`` (at the project root, or inside ``src/`` or ``app/``). ``api.py``
is not one of those names, so this module re-exports the application it
creates.

Local commands keep using ``flask --app api:app`` – this file changes nothing
about how the app behaves, it only gives Vercel a recognised filename.
"""

from api import app  # noqa: F401
