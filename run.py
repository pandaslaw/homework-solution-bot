import uvicorn
from src.config import app_settings
from src.main import app

if __name__ == "__main__":
    port = int(app_settings.PORT if hasattr(app_settings, 'PORT') else 5000)
    uvicorn.run(
        "src.main:app",
        host="0.0.0.0",
        port=port,
        reload=True,  # Enable auto-reload during development
        workers=4  # Number of worker processes for handling requests
    )
