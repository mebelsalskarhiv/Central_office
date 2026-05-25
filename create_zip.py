"""
Create ZIP archive of OrderManager Portable bundle
"""
import zipfile
import os
from pathlib import Path

def create_zip():
    bundle_dir = Path("OrderManager_Portable")
    zip_path = Path("OrderManager_Portable_v1.0.zip")

    print(f"Creating ZIP archive: {zip_path}")
    print(f"Source directory: {bundle_dir}")

    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as zipf:
        file_count = 0
        for root, dirs, files in os.walk(bundle_dir):
            for file in files:
                file_path = Path(root) / file
                arcname = file_path.relative_to(bundle_dir.parent)
                print(f"Adding: {arcname}")
                zipf.write(file_path, arcname)
                file_count += 1

    zip_size = zip_path.stat().st_size / (1024 * 1024)
    print(f"\nZIP created successfully!")
    print(f"Files archived: {file_count}")
    print(f"Archive size: {zip_size:.1f} MB")

if __name__ == "__main__":
    create_zip()
