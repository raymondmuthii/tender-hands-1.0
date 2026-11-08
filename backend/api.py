"""Vercel serverless entry point.

Vercel looks for `app` at the module level.
"""

from app import create_app

app = create_app()

if __name__ == "__main__":
    app.run(debug=True)
