import zipfile
import os

zip_filename = 'agriguard_ai_project.zip'
exclude_dirs = {'__pycache__', '.git', '.venv', 'venv', 'scratch'}

with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
    for root, dirs, files in os.walk('.'):
        dirs[:] = [d for d in dirs if d not in exclude_dirs and not d.startswith('.')]
        for file in files:
            if file != zip_filename and not file.endswith('.pyc'):
                filepath = os.path.join(root, file)
                arcname = os.path.relpath(filepath, '.')
                zipf.write(filepath, arcname)

print(f"Successfully created {zip_filename} with size {os.path.getsize(zip_filename)} bytes")
