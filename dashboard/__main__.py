"""Allow running with `python -m dashboard`."""

from dashboard.app import app

app.run(debug=True, port=8050)
