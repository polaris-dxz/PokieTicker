"""Production entry: run uvicorn with PORT from environment (e.g. Render, Fly.io)."""
import os

if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8000"))
    import uvicorn
    uvicorn.run(
        "server.api.main:app",
        host="0.0.0.0",
        port=port,
    )
