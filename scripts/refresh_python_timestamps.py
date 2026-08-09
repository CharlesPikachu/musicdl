from pathlib import Path
import os
import time


def update_python_file_timestamps(directory: Path) -> None:
    """Update the modification time of all Python files in the given directory."""
    if not directory.exists():
        raise FileNotFoundError(f"Directory does not exist: {directory}")

    if not directory.is_dir():
        raise NotADirectoryError(f"Path is not a directory: {directory}")

    timestamp = time.time()
    updated_count = 0
    failed_count = 0

    for file_path in sorted(directory.glob("*.py")):
        try:
            # Preserve the original access time and update only the modification time.
            stat = file_path.stat()
            os.utime(file_path, (stat.st_atime, timestamp))

            print(f"Updated: {file_path.name}")
            updated_count += 1

        except OSError as exc:
            print(f"Failed to update {file_path.name}: {exc}")
            failed_count += 1

    print(
        f"\nCompleted: {updated_count} file(s) updated, "
        f"{failed_count} file(s) failed."
    )


def main() -> None:
    update_python_file_timestamps(Path.cwd())


if __name__ == "__main__":
    main()