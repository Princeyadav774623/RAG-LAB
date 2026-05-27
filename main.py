import sys
import argparse
import os

def main():
    parser = argparse.ArgumentParser(description="Production-Grade RAG System Command Line Manager")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--ui", action="store_true", help="Launch the premium Streamlit interactive dashboard UI")
    group.add_argument("--api", action="store_true", help="Launch the FastAPI production-grade REST backend API service")
    
    parser.add_argument("--port", type=int, help="Override default port (UI defaults to 8501, API defaults to 8000)")
    
    args = parser.parse_args()
    
    # Locate project absolute path
    project_dir = os.path.dirname(os.path.abspath(__file__))
    
    if args.ui:
        port = args.port if args.port else 8501
        print(f"[*] Starting Streamlit Dashboard on port {port}...")
        # Execute streamlit run command in-process
        import subprocess
        try:
            cmd = [sys.executable, "-m", "streamlit", "run", os.path.join(project_dir, "app.py"), "--server.port", str(port)]
            subprocess.run(cmd, check=True)
        except KeyboardInterrupt:
            print("\n[-] Streamlit Dashboard stopped.")
        except Exception as e:
            print(f"\n[!] Error starting Streamlit: {e}")
            
    elif args.api:
        port = args.port if args.port else 8000
        print(f"[*] Starting FastAPI Production Server on port {port}...")
        print(f"[🚀] Access the premium Apple-style RAG UI at: http://localhost:{port}/")
        import uvicorn
        try:
            uvicorn.run("api:app", host="0.0.0.0", port=port, reload=True)
        except KeyboardInterrupt:
            print("\n[-] FastAPI Production Server stopped.")
        except Exception as e:
            print(f"\n[!] Error starting FastAPI: {e}")

if __name__ == "__main__":
    main()
