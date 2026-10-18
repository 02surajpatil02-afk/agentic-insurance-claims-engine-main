"""
Launcher script for Autonomous Enterprise Workflow Agent Server.
Builds the frontend SPA if needed and launches FastAPI on http://localhost:8000
"""

import os
import subprocess
import sys
from pathlib import Path

def main():
    print("=" * 80)
    print("  AUTONOMOUS ENTERPRISE WORKFLOW AGENT — SERVER LAUNCHER")
    print("=" * 80)

    frontend_dir = Path("frontend")
    dist_dir = frontend_dir / "dist"

    if frontend_dir.exists() and not dist_dir.exists():
        print("Building frontend single-page application...")
        try:
            subprocess.run("npm run build", shell=True, cwd=frontend_dir, check=True)
            print("Frontend built successfully!")
        except Exception as e:
            print(f"Warning: Could not build frontend automatically ({e}). Server will run in API-only mode.")

    print("\nStarting Uvicorn web server on http://localhost:8000 ...")
    print("Access Web UI Dashboard at: http://localhost:8000")
    print("Access OpenAPI Documentation at: http://localhost:8000/docs")
    print("Press Ctrl+C to terminate server.\n")

    import uvicorn
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=False)

if __name__ == "__main__":
    main()
