#!/usr/bin/env python3
"""
Simple test to run FastAPI server from main directory
"""
import sys
import os

# Add current directory to path
sys.path.insert(0, os.getcwd())

try:
    from backend.app.main import app
    print("SUCCESS: Successfully imported FastAPI app")

    # Test basic app creation
    print("SUCCESS: FastAPI app object created")
    print(f"SUCCESS: App title: {app.title}")
    print(f"SUCCESS: App version: {app.version}")

    # Try to get routes
    routes = []
    for route in app.routes:
        if hasattr(route, 'path') and hasattr(route, 'methods'):
            for method in getattr(route, 'methods', ['GET']):
                routes.append(f"{method} {route.path}")

    print(f"SUCCESS: Total API routes: {len(routes)}")

    # Look for pipeline routes specifically
    pipeline_routes = [r for r in routes if '/pipeline' in r]
    print(f"SUCCESS: Pipeline routes found: {len(pipeline_routes)}")

    if pipeline_routes:
        print("Pipeline routes:")
        for route in pipeline_routes[:5]:  # Show first 5
            print(f"  - {route}")

    print("\nINFO: Starting server on localhost:8002...")

except Exception as e:
    print(f"ERROR: Error importing app: {e}")
    import traceback
    traceback.print_exc()

if __name__ == "__main__":
    try:
        import uvicorn
        from backend.app.main import app
        uvicorn.run(app, host="127.0.0.1", port=8002)
    except Exception as e:
        print(f"ERROR: Error starting server: {e}")