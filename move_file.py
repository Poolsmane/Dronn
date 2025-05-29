# move_file.py

import os
import time
import shutil
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

downloads_folder = os.path.expanduser('~/Downloads')
target_folder = '/home/kartikeyapatel/Videos/gem/extracted_data'
path_file = '/home/kartikeyapatel/Videos/gem/latest_moved_path.txt'  # <- shared path file

class DownloadHandler(FileSystemEventHandler):
    def on_created(self, event):
        if not event.is_directory:
            base_name = os.path.basename(event.src_path)
            if base_name.endswith('.crdownload'):
                actual_name = base_name.replace('.crdownload', '')
                actual_path = os.path.join(downloads_folder, actual_name)
                crdownload_path = event.src_path

                print(f"New file is downloading: {actual_name}")

                # Wait until the .crdownload disappears and final file exists
                while os.path.exists(crdownload_path) or not os.path.exists(actual_path):
                    print("Waiting for file to finish downloading...")
                    time.sleep(1)

                print(f"Download complete: {actual_name}")
                time.sleep(1)

                target_path = os.path.join(target_folder, actual_name)
                try:
                    shutil.move(actual_path, target_path)
                    print(f"Moved file to: {target_path}")

                    with open(path_file, "w") as f:
                        f.write(target_path)
                except Exception as e:
                    print(f"Error moving file: {e}")
            else:
                # Case: non-crdownload file created directly
                print(f"File created without .crdownload: {base_name}")
                time.sleep(1)
                target_path = os.path.join(target_folder, base_name)
                try:
                    shutil.move(event.src_path, target_path)
                    print(f"Moved file to: {target_path}")
                    with open(path_file, "w") as f:
                        f.write(target_path)
                except Exception as e:
                    print(f"Error moving direct file: {e}")



def run_task():
    event_handler = DownloadHandler()
    observer = Observer()
    observer.schedule(event_handler, downloads_folder, recursive=False)
    observer.start()
    print("Watching Downloads folder...")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt as e:
        print(e)
        observer.stop()
    observer.join()





