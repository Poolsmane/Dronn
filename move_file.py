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
    except KeyboardInterrupt:
        observer.stop()
    observer.join()






# import os
# import time
# import shutil
# from watchdog.observers import Observer
# from watchdog.events import FileSystemEventHandler

# # Set the directories
# downloads_folder = os.path.expanduser('~/Downloads')
# target_folder = '/home/kartikeyapatel/Videos/gem/extracted_data'  # Replace with your target folder path

# class DownloadHandler(FileSystemEventHandler):
#     def on_created(self, event):
#         # Check if the event is a file (not a directory)
#         if not event.is_directory:
#             file_name = os.path.basename(event.src_path)
#             print(f"New file downloaded: {file_name}")
            
#             # Check if the file has finished downloading
#             # Files may end with .crdownload when not fully downloaded
#             while file_name.endswith('.crdownload'):
#                 print("File is still downloading, waiting...")
#                 time.sleep(2)
#                 file_name = os.path.basename(event.src_path)

#             # Now the file should be fully downloaded
#             print(f"File download complete: {file_name}")

#             # Wait a bit to ensure the file is completely downloaded
#             time.sleep(2)
            
#             # Move the file to the target folder
#             target_path = os.path.join(target_folder, file_name)
#             try:
#                 shutil.move(event.src_path, target_path)
#                 print(f"Moved file to: {target_path}")
#             except FileNotFoundError:
#                 print(f"Error: File not found: {event.src_path}")
#             except Exception as e:
#                 print(f"An error occurred while moving the file: {e}")

# # Set up the observer to monitor the Downloads folder
# event_handler = DownloadHandler()
# observer = Observer()
# observer.schedule(event_handler, downloads_folder, recursive=False)

# # Start the observer
# observer.start()

# try:
#     while True:
#         time.sleep(1)
# except KeyboardInterrupt:
#     observer.stop()
# observer.join()