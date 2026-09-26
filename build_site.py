"""Build Zensical docs and copy the browser-only generator into the site tree."""
from pathlib import Path
import shutil
import subprocess


ROOT = Path(__file__).resolve().parent
WEB = ROOT / "web"
DESTINATION = ROOT / "site" / "tools" / "patient-list-generator"
ASSETS = ("index.html", "style.css", "app.mjs", "csv.mjs")


def stage() -> None:
    DESTINATION.mkdir(parents=True, exist_ok=True)
    for name in ASSETS:
        source = WEB / name
        if source.is_symlink() or not source.is_file():
            raise ValueError(f"invalid browser asset: {name}")
        shutil.copyfile(source, DESTINATION / name)
    (ROOT / "site" / "_headers").write_text(
        "/tools/patient-list-generator/*\n"
        "  Content-Security-Policy: default-src 'self'; script-src 'self'; style-src 'self'; "
        "img-src 'self' data:; connect-src 'none'; form-action 'none'; base-uri 'none'; "
        "object-src 'none'; frame-ancestors 'none'\n"
        "  Referrer-Policy: no-referrer\n"
        "  X-Content-Type-Options: nosniff\n"
        "  X-Frame-Options: DENY\n"
        "  Permissions-Policy: camera=(), microphone=(), geolocation=()\n",
        encoding="utf-8",
    )
    print(f"Site ready: {ROOT / 'site'}")


def build() -> None:
    subprocess.run(["zensical", "build", "--strict"], cwd=ROOT, check=True)
    stage()


if __name__ == "__main__":
    build()
