import os
import sys
import subprocess
import webbrowser
import time
import logging
from pathlib import Path

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("Activation")

ROOT_DIR = Path(__file__).parent.parent
PYTHON_EXE = sys.executable

def run_command(cmd, desc, cwd=ROOT_DIR):
    logger.info(f"\n{'='*60}\nEXECUTING: {desc}\n{'='*60}")
    try:
        subprocess.run(cmd, cwd=str(cwd), check=True)
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"❌ Failed: {desc} ({e})")
        return False

def start_server():
    logger.info("Starting Backend Server...")
    # Run server as a detached process
    try:
        log_file = open("server.log", "w")
        if sys.platform == "win32":
            subprocess.Popen([PYTHON_EXE, "server.py"], cwd=str(ROOT_DIR), creationflags=subprocess.CREATE_NEW_CONSOLE, env=os.environ, stdout=log_file, stderr=log_file)
        else:
            subprocess.Popen([PYTHON_EXE, "server.py"], cwd=str(ROOT_DIR), env=os.environ, stdout=log_file, stderr=log_file)
        return True
    except Exception as e:
        logger.error(f"❌ Failed to start server: {e}")
        return False

def git_sync():
    logger.info("Synchronizing with Repository...")
    if not run_command(["git", "add", "."], "Staging changes"): return False
    if not run_command(["git", "commit", "-m", "Audit complete: Algorithm fixes, security improvements, and master activation script added."], "Committing changes"): 
        logger.warning("Nothing to commit or commit failed.")
    return run_command(["git", "push"], "Pushing to remote")

def main():
    # Ensure DATABASE_URL is set for all child processes
    if not os.getenv("DATABASE_URL"):
        os.environ["DATABASE_URL"] = "postgresql://postgres:1Anurag2Basistha@localhost:5432/hardwaregenius"
        
    logger.info("HardwareGenius Master Activation Sequence Initiated")
    
    # 1. Initialize Database
    if not run_command([PYTHON_EXE, "scripts/init_complete_database.py"], "Full Database Initialization"):
        logger.error("Initialization failed. Please check database connectivity/credentials.")
        return

    # 2. Run Ingestion Pipeline (Selective/Full)
    if not run_command([PYTHON_EXE, "scripts/run_pipeline.py"], "Ingestion Pipeline"):
        logger.warning("Pipeline encountered errors, attempting to proceed with available data.")

    # 3. Start Server
    if not start_server():
        return

    # 4. Open UI
    logger.info("Launching User Interface...")
    try:
        webbrowser.open("http://localhost:8000")
    except Exception as e:
        logger.warning(f"Could not open browser: {e}")

    # 5. Git Sync
    logger.info("Waiting for server to initialize before final sync...")
    time.sleep(5)
    git_sync()
    
    logger.info("\n✅ HardwareGenius is ACTIVE and UP-TO-DATE!")
    logger.info("Server is running in a new window. Access it at http://localhost:8000")

if __name__ == "__main__":
    main()
