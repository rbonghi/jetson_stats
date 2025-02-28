import multiprocessing
import time
import os
import io
import pstats
import cProfile

# jtop service
from jtop.service import JtopServer
# jtop client
from jtop import jtop, JtopException


TOTAL_TIME = 20  # Total time to run the server and clients
NUM_CLIENTS = 1  # Number of clients to spawn
RECONNECT = 0  # Reconnect time for the client
INTERVAL = 0.2  # Duration for the server to run


def profile_function(func, filename):
    """Profiles a function execution for a limited duration and saves the stats."""
    profiler = cProfile.Profile()
    profiler.enable()

    func()

    profiler.disable()
    profiler.dump_stats(filename)
    print(f"[Profiler] Saved profiling data to {filename}")


if __name__ == "__main__":
    profile_folder = os.path.join(os.path.dirname(__file__), "profile")
    if not os.path.exists(profile_folder):
        os.makedirs(profile_folder)

    def start_server():
        # Initialize stats server
        server = JtopServer(force=True)
        server.loop_for_ever(run_time=TOTAL_TIME)

    def start_client(client_id):
        start_time = time.time()
        time.sleep(2)
        try:
            with jtop(interval=INTERVAL) as jetson:
                while jetson.ok():
                    # Check if the total time has expired
                    if time.time() - start_time >= TOTAL_TIME:
                        print(f"[Client {client_id}] Shutting down.")
                        break
                    print(jetson.stats)
        except JtopException as e:
            print(f"[Client {client_id}] {e}")

    # Profile the server inside the main process
    server_profiler = multiprocessing.Process(
        target=profile_function, args=(start_server, os.path.join(profile_folder, "server_profile.prof"))
    )

    client_processes = []

    for i in range(NUM_CLIENTS):
        client_profiler = multiprocessing.Process(
            target=profile_function, args=(lambda: start_client(i), os.path.join(profile_folder, f"client_{i}_profile.prof"))
        )
        client_processes.append(client_profiler)

    server_profiler.start()

    for cp in client_processes:
        cp.start()

    for cp in client_processes:
        cp.join()

    server_profiler.join()

    # Change the ownership of the profile folder and its contents to the sudo user
    sudo_user = os.getenv("SUDO_USER")
    if sudo_user:
        uid = int(os.popen(f"id -u {sudo_user}").read().strip())
        gid = int(os.popen(f"id -g {sudo_user}").read().strip())
        for root, dirs, files in os.walk(profile_folder):
            for dir_name in dirs:
                os.chown(os.path.join(root, dir_name), uid, gid)
            for file_name in files:
                os.chown(os.path.join(root, file_name), uid, gid)
            os.chown(profile_folder, uid, gid)
        print(f"[Ownership] Changed ownership of {profile_folder} and its contents to {sudo_user}")
    else:
        print("[Ownership] No sudo user found, skipping ownership change.")

    print("[Main] All processes terminated and profiling complete.")
# EOF
