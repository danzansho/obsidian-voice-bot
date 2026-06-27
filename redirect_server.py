import urllib.parse
from fastapi import FastAPI, Query
from fastapi.responses import HTMLResponse

app = FastAPI()

@app.get("/open")
async def open_obsidian(name: str = Query(...), content: str = Query(...)):
    # URL encode parameters safely for the deep link
    encoded_title = urllib.parse.quote(name)
    encoded_content = urllib.parse.quote(content)
    obsidian_uri = f"obsidian://new?name={encoded_title}&content={encoded_content}".replace('_', '%5F')

    # HTML with JavaScript redirect (the most bulletproof way for mobile WebViews)
    html_content = f"""
    <html>
    <head>
        <title>Redirecting to Obsidian...</title>
        <script>
            window.onload = function() {{
                window.location.href = "{obsidian_uri}";
                setTimeout(function() {{
                    window.close();
                }}, 1000);
            }};
        </script>
    </head>
    <body style="background-color: #1e1e1e; color: #ffffff; font-family: sans-serif; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0;">
        <div style="text-align: center;">
            <p style="font-size: 1.2em;">Opening your note in Obsidian...</p>
        </div>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content, status_code=200)