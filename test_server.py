import subprocess
import time

print("Starting uvicorn server...")
process = subprocess.Popen(
    ["python", "-m", "uvicorn", "api.main:app", "--port", "8005"],
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    text=True,
    cwd=r"c:\Android Projects\accenture\digitaltwin-ai"
)

start_time = time.time()
found_error = False

# Wait for 3 minutes (180 seconds)
while time.time() - start_time < 180:
    # Check if process exited early
    if process.poll() is not None:
        print("Process exited early.")
        break
    time.sleep(1)

# Terminate process
process.terminate()
try:
    process.wait(timeout=5)
except subprocess.TimeoutExpired:
    process.kill()

print("Server stopped. Reading output...")
stdout, _ = process.communicate()
if "Error in simulation loop" in stdout:
    print("YES - Error in simulation loop was found.")
else:
    print("NO - Error in simulation loop was not found.")
