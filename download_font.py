import urllib.request
import os

def download_font():
    os.makedirs("d:/Code/cookie-dash-game/assets/fonts", exist_ok=True)
    url = "https://github.com/google/fonts/raw/main/ofl/pressstart2p/PressStart2P-Regular.ttf"
    dest = "d:/Code/cookie-dash-game/assets/fonts/PressStart2P-Regular.ttf"
    print(f"Downloading {url} to {dest}...")
    urllib.request.urlretrieve(url, dest)
    print("Done!")

if __name__ == "__main__":
    download_font()
