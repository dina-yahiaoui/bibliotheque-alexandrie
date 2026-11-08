import json
import time
from pathlib import Path

import requests
import yaml


def load_config():
    """Lit config.yaml et renvoie son contenu."""
    with open("config.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f)


def page_to_url(page, site_base_url):
    """Transforme 'tutorial/first-steps.md' en lien du site."""
    path = page.removesuffix(".md")
    if path.endswith("index"):
        path = path[: -len("index")]
    else:
        path += "/"
    return site_base_url + path   

def main():
    config = load_config()["corpus"]
    out_dir = Path(config["output_dir"])
    out_dir.mkdir(parents=True, exist_ok=True)

    manifest = []
    for page in config["pages"]:
        raw_url = config["raw_base_url"] + page
        try:
            response = requests.get(raw_url, timeout=20)
            response.raise_for_status()
        except requests.RequestException as error:
            print(f"[ÉCHEC] {page} : {error}")
            continue

        filename = page.replace("/", "__")
        (out_dir / filename).write_text(response.text, encoding="utf-8")

        manifest.append({
            "file": filename,
            "source_url": page_to_url(page, config["site_base_url"]),
        })
        print(f"[OK] {page}")
        time.sleep(0.3)

    with open(out_dir / "manifest.json", "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)

    print(f"\n{len(manifest)}/{len(config['pages'])} pages téléchargées")


if __name__ == "__main__":
    main()