import os
import pstats
import subprocess

def analyze_data(file):
    file_path = os.path.join(os.path.dirname(__file__), "profile", file)
    if os.path.isfile(file_path) and file.endswith(".prof"):
        stats = pstats.Stats(file_path)
        stats.strip_dirs()
        stats.sort_stats(pstats.SortKey.CUMULATIVE)
        stats.print_stats(10)  # Print top 10 functions by cumulative time spent

        highest = None
        if stats.stats:
            func, stats = max(stats.stats.items(), key=lambda item: (item[1][2], item[1][1]))  # Sort by 'tt' (total time) and 'nc' (number of calls)
            highest = {
            'func_name': func[2],
            'cc': stats[0],
            }
    return highest


if __name__ == "__main__":
    profile_folder = os.path.join(os.path.dirname(__file__), "profile")
    if not os.path.exists(profile_folder):
        print(f"Profile folder '{profile_folder}' does not exist. Exiting.")
        exit(1)
    files = os.listdir(profile_folder)
    for file in files:
        if highest:= analyze_data(file):
            print(f"Call count: {highest['cc']}, Function with the highest call count: {highest['func_name']}")
# EOF
