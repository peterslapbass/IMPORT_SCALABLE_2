import sys
import threading
from dash import Dash
import layout
import callbacks
import os

os.chdir(os.path.dirname(os.path.abspath(__file__)))

app = Dash(__name__, suppress_callback_exceptions=True)

# Inline script to apply saved theme before render (prevents flash)
app.index_string = '''
<!DOCTYPE html>
<html>
<head>
  <script>
    (function() {
      var theme = localStorage.getItem('theme') || 'dark';
      document.documentElement.setAttribute('data-theme', theme);
    })();
  </script>
  {%metas%}
  <title>{%title%}</title>
  {%favicon%}
  {%css%}
</head>
<body>
  {%app_entry%}
  <footer>
    {%config%}
    {%scripts%}
    {%renderer%}
  </footer>
</body>
</html>
'''

app.layout = layout.create_layout(app)
callbacks.register_callbacks(app)

def run_server():
    app.run(debug=False, use_reloader=False)

if __name__ == '__main__':
    if '--browser' in sys.argv:
        run_server()
    else:
        import urllib.request
        import time
        import webview

        t = threading.Thread(target=run_server, daemon=True)
        t.start()

        for _ in range(30):
            try:
                urllib.request.urlopen("http://127.0.0.1:8050")
                break
            except:
                time.sleep(0.5)

        webview.create_window("ImportRealMod", "http://127.0.0.1:8050",
                               maximized=True)
        webview.start(gui='edgechromium')
