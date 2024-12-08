import os
import time
import threading
from datetime import datetime


# Abstract Base Class for all file types
class File:
    def __init__(self, path):
        self.path = path
        self.filename = os.path.basename(path)
        self.extension = os.path.splitext(path)[1]
        self.creation_date = datetime.fromtimestamp(os.path.getctime(path))
        self.last_updated_date = datetime.fromtimestamp(os.path.getmtime(path))

    def info(self):
        return {
            'Filename': self.filename,
            'Extension': self.extension,
            'Creation Date': self.creation_date,
            'Last Updated Date': self.last_updated_date
        }

    def has_changed(self):
        current_mtime = os.path.getmtime(self.path)
        return self.last_updated_date.timestamp() != current_mtime

    def update_last_modified(self):
        self.last_updated_date = datetime.fromtimestamp(os.path.getmtime(self.path))


# Specialized class for Image Files
class ImageFile(File):
    def info(self):
        info = super().info()
        info['Dimensions'] = 'N/A (Requires external library)'
        return info


class TextFile(File):
    def __init__(self, path):
        super().__init__(path)
        self.content_hash = self.compute_content_hash()

    def compute_content_hash(self):
        """Compute a simple hash of the file's content by summing the length of each line."""
        try:
            with open(self.path, 'r', encoding='utf-8') as file:
                content = file.read()
                return hash(content)
        except Exception as e:
            return None

    def has_content_changed(self):
        """Check if the content of the file has changed."""
        current_hash = self.compute_content_hash()
        return current_hash != self.content_hash

    def update_last_modified(self):
        super().update_last_modified()
        self.content_hash = self.compute_content_hash()

    def info(self):
        info = super().info()
        try:
            with open(self.path, 'r', encoding='utf-8') as file:
                content = file.readlines()
                info['Line Count'] = len(content)
                info['Word Count'] = sum(len(line.split()) for line in content)
                info['Character Count'] = sum(len(line) for line in content)
        except Exception as e:
            info['Line Count'] = info['Word Count'] = info['Character Count'] = 'Unable to read'
        return info


class ProgramFile(File):
    def info(self):
        info = super().info()
        try:
            with open(self.path, 'r', encoding='utf-8') as file:
                content = file.readlines()
                info['Line Count'] = len(content)
                info['Class Count'] = sum(1 for line in content if 'class ' in line)
                info['Method Count'] = sum(1 for line in content if 'def ' in line)
        except Exception as e:
            info['Line Count'] = info['Class Count'] = info['Method Count'] = 'Unable to read'
        return info


# Main File Monitor System
class FileMonitor:
    FILE_TYPES = {
        '.png': ImageFile,
        '.jpg': ImageFile,
        '.jpeg': ImageFile,
        '.txt': TextFile,
        '.py': ProgramFile,
        '.java': ProgramFile
    }

    def __init__(self, folder_path):
        self.folder_path = folder_path
        self.files = {}
        self.last_displayed_state = {}
        self.snapshot_time = datetime.now()
        self.scan_files()

    def scan_files(self):
        """Scan the folder and create objects for each file."""
        current_files = {}
        for filename in os.listdir(self.folder_path):
            file_path = os.path.join(self.folder_path, filename)
            if os.path.isfile(file_path):
                ext = os.path.splitext(filename)[1].lower()
                file_class = self.FILE_TYPES.get(ext, File)
                current_files[filename] = file_class(file_path)

        self.detect_changes(current_files)
        self.files = current_files

    def detect_changes(self, current_files):
        """Detect file changes, additions, and deletions."""
        old_files = set(self.files.keys())
        new_files = set(current_files.keys())

        added_files = new_files - old_files
        deleted_files = old_files - new_files
        changed_files = []

        for filename in old_files & new_files:
            if self.files[filename].has_changed():
                changed_files.append(filename)
                self.files[filename].update_last_modified()

        changes_to_display = []

        # Prepare messages for added files
        for filename in added_files:
            if filename not in self.last_displayed_state or self.last_displayed_state[filename] != 'added':
                changes_to_display.append(f"[INFO] {filename} is a new file.")
                self.last_displayed_state[filename] = 'added'

        # Prepare messages for deleted files
        for filename in deleted_files:
            if filename not in self.last_displayed_state or self.last_displayed_state[filename] != 'deleted':
                changes_to_display.append(f"[INFO] {filename} was deleted.")
                self.last_displayed_state[filename] = 'deleted'

        # Prepare messages for changed files
        for filename in changed_files:
            if filename not in self.last_displayed_state or self.last_displayed_state[filename] != 'changed':
                changes_to_display.append(f"[INFO] {filename} has changed.")
                if filename.endswith('.txt') and self.files[filename].has_content_changed():
                    changes_to_display.append(f"[INFO] A modification was detected in the document '{filename}'.")
                self.last_displayed_state[filename] = 'changed'

        if changes_to_display:
            for change in changes_to_display:
                print(change)

    def commit(self):
        """Commit the current state of the system."""
        self.snapshot_time = datetime.now()
        for file in self.files.values():
            file.update_last_modified()
        print(f"[INFO] Snapshot committed at {self.snapshot_time}.")

    def info(self, filename):
        """Display file information."""
        file_obj = self.files.get(filename)
        if file_obj:
            for key, value in file_obj.info().items():
                print(f"{key}: {value}")
        else:
            print(f"[INFO] File '{filename}' not found.")

    def status(self):
        """Show the change status of each file."""
        for filename, file_obj in self.files.items():
            status = 'changed' if file_obj.has_changed() else 'unchanged'
            print(f"[INFO] {filename}: {status}")

    def real_time_monitor(self):
        """Monitor the folder for changes in real time."""
        while True:
            time.sleep(1)  # Scan every second
            self.scan_files()


# Interactive Console
class Console:
    def __init__(self, folder_path):
        self.file_monitor = FileMonitor(folder_path)

    def start(self):
        """Start the interactive console and background monitor."""
        threading.Thread(target=self.file_monitor.real_time_monitor, daemon=True).start()

        while True:
            command = input("Enter command (commit, info <filename>, status, exit): ").strip()
            if command == 'exit':
                print("[INFO] Exiting the program...")
                break
            elif command == 'commit':
                self.file_monitor.commit()
            elif command.startswith('info '):
                filename = command.split(' ', 1)[1]
                self.file_monitor.info(filename)
            elif command == 'status':
                self.file_monitor.status()
            else:
                print("[INFO] Unknown command. Available commands: commit, info <filename>, status, exit.")


if __name__ == "__main__":
    # Specify the folder to monitor
    folder_path = r"C:\Users\user\Desktop\TEST"

    # Create the folder if it doesn't exist
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)

    console = Console(folder_path)
    console.start()
