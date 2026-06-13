from dash import Dash
from dotenv import load_dotenv

from journey.ui.callbacks import register_callbacks
from journey.ui.layout import build_layout

load_dotenv()

app = Dash(__name__, title="Journey Harness")
server = app.server
app.layout = build_layout
register_callbacks(app)

if __name__ == "__main__":
    app.run(debug=True)
