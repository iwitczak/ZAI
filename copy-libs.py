import shutil
import os


FILES_TO_COPY = {
    "css": [
        "bootstrap/dist/css/bootstrap.min.css",
        "font-awesome/css/font-awesome.min.css",
    ],
    "fonts": [
        "font-awesome/fonts/fontawesome-webfont.woff2",
    ],
    "js": [
        "bootstrap/dist/js/bootstrap.bundle.min.js",
        "echarts/dist/echarts.min.js",
        "vue/dist/vue.global.prod.js",
    ],
}

SOURCE_DIR = "node_modules"
DEST_DIR = os.path.join("static", "vendor")


def copy_vendor_files():
    for subfolder, paths in FILES_TO_COPY.items():
        dest_subdir = os.path.join(DEST_DIR, subfolder)
        os.makedirs(dest_subdir, exist_ok=True)

        for relative_path in paths:
            src = os.path.join(SOURCE_DIR, relative_path)
            filename = os.path.basename(relative_path)
            dst = os.path.join(dest_subdir, filename)

            if os.path.exists(src):
                shutil.copy2(src, dst)
                print(f"✓  {src}  →  {dst}")
            else:
                print(f"✗  Nie znaleziono: {src}")


if __name__ == "__main__":
    copy_vendor_files()