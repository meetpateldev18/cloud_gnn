import os
import sys

REQUIRED_FILES = [
    "dataset/machine_events.csv",
    "dataset/task_events.csv",
    "dataset/job_events.csv",
]


def verify_dataset(base_path: str = ".") -> bool:
    """Check that all required dataset files exist and print status."""
    missing = []
    for f in REQUIRED_FILES:
        full = os.path.join(base_path, f)
        if not os.path.isfile(full):
            missing.append(f)

    if missing:
        print("\n[ERROR] The following dataset files are MISSING:\n")
        for m in missing:
            print(f"  ✗  {m}")
        print(
            "\nPlease download the Google Cluster Workload Trace dataset from:"
            "\n  https://www.kaggle.com/datasets/derrickmwiti/google-2019-cluster-sample"
            "\n\nThen place the CSV files in the dataset/ folder:"
            "\n  cloud_scheduler/dataset/machine_events.csv"
            "\n  cloud_scheduler/dataset/task_events.csv"
            "\n  cloud_scheduler/dataset/job_events.csv\n"
        )
        return False

    print("[OK] All dataset files found.")
    return True


if __name__ == "__main__":
    base = sys.argv[1] if len(sys.argv) > 1 else "."
    ok = verify_dataset(base)
    sys.exit(0 if ok else 1)
