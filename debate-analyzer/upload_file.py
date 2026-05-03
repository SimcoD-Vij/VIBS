import requests
import sys
import os

file_path = r"D:\Mini project\Voice\debate voice.m4a"
url = "http://localhost:8000/api/upload"

if not os.path.exists(file_path):
    print(f"Error: File not found at {file_path}")
    sys.exit(1)

print(f"Uploading {file_path} to {url}...")

with open(file_path, 'rb') as f:
    files = {'file': (os.path.basename(file_path), f, 'audio/mp4')}
    response = requests.post(url, files=files)

if response.status_code == 200:
    print("Upload successful!")
    print(response.json())
else:
    print(f"Upload failed with status code {response.status_code}")
    print(response.text)
