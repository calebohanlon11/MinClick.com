from website import create_app
import sys
import os

if __name__ == "__main__":
    try:
        app = create_app()
        print("=" * 50)
        print("Flask server starting...")
        print("Server will be available at: http://127.0.0.1:5000")
        print("Press CTRL+C to stop the server")
        print("=" * 50)
        app.run(debug=True, host='127.0.0.1', port=5000, use_reloader=False)
    except Exception as e:
        print(f"Error starting server: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
