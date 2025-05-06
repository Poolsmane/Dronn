# file2.py

import os
import time
import shutil
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

downloads_folder = os.path.expanduser('~/Downloads')
target_folder = '/home/kartikeyapatel/Videos/gem/extracted_data'

class DownloadHandler(FileSystemEventHandler):
    def on_created(self, event):
        if not event.is_directory:
            file_name = os.path.basename(event.src_path)
            print(f"New file downloaded: {file_name}")

            while file_name.endswith('.crdownload'):
                print("File is still downloading, waiting...")
                time.sleep(2)
                file_name = os.path.basename(event.src_path)

            print(f"File download complete: {file_name}")
            time.sleep(2)

            target_path = os.path.join(target_folder, file_name)
            try:
                shutil.move(event.src_path, target_path)
                print(f"Moved file to: {target_path}")
            except FileNotFoundError:
                print(f"Error: File not found: {event.src_path}")
            except Exception as e:
                print(f"An error occurred while moving the file: {e}")

def run_task():
    event_handler = DownloadHandler()
    observer = Observer()
    observer.schedule(event_handler, downloads_folder, recursive=False)
    observer.start()
    print("Observer started, monitoring Downloads folder...")

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