"""Наповнює каталог даних демонстраційними користувачами й файлами.

python scripts/seed_demo.py data/demo
Користувач: Maryna / demo123
"""
from __future__ import annotations

import io
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from PIL import Image, ImageDraw  # noqa: E402

from cloudfolder.server.app import create_app  # noqa: E402


def png(color, label, size=(480, 300)) -> bytes:
    img = Image.new("RGB", size, color)
    d = ImageDraw.Draw(img)
    for i in range(0, size[0], 40):
        d.line([(i, 0), (i, size[1])], fill=tuple(min(255, c + 25) for c in color))
    d.ellipse([size[0] // 2 - 70, 60, size[0] // 2 + 70, 200], fill=(255, 255, 255))
    d.text((20, size[1] - 40), label, fill=(255, 255, 255))
    buf = io.BytesIO()
    img.save(buf, "PNG")
    return buf.getvalue()


XML = """<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0">
    <modelVersion>4.0.0</modelVersion>
    <groupId>ua.univ.lab</groupId>
    <artifactId>cloud-folder-demo</artifactId>
    <version>1.0.0</version>
    <properties>
        <maven.compiler.source>17</maven.compiler.source>
        <maven.compiler.target>17</maven.compiler.target>
    </properties>
    <dependencies>
        <dependency>
            <groupId>org.junit.jupiter</groupId>
            <artifactId>junit-jupiter</artifactId>
            <version>5.10.2</version>
            <scope>test</scope>
        </dependency>
    </dependencies>
</project>
"""

JAVA = """package ua.univ.lab;

public class Main {
    public static void main(String[] args) {
        System.out.println("Привіт, хмарне сховище!");
    }
}
"""

DEMO = [
    # name, data, minutes after T0 for creation, minutes for modification
    ("pom.xml", XML.encode(), 0, 340),
    ("Main.java", JAVA.encode(), 15, 75),
    ("logo.png", png((47, 111, 222), "logo.png"), 30, 30),
    ("settings.xml", b'<?xml version="1.0"?>\n<settings>\n  <theme>dark</theme>\n  <lang>uk</lang>\n</settings>\n', 60, 610),
    ("diagram.png", png((214, 96, 40), "diagram.png"), 90, 220),
    ("FileUtils.java", b"package ua.univ.lab;\n\nfinal class FileUtils {\n    private FileUtils() {}\n}\n", 120, 500),
    ("notes.txt", "Нотатки до проєкту\n".encode(), 150, 160),
    ("budget.csv", b"item,amount\nhosting,0\ndomain,0\n", 200, 260),
    ("screenshot.png", png((40, 140, 90), "screenshot.png"), 240, 720),
]


def main(data_dir: str) -> None:
    app = create_app(data_dir, web_dist=Path(data_dir) / "_none")
    auth, files = app.state.auth, app.state.files
    t0 = datetime(2026, 11, 17, 9, 0, tzinfo=timezone.utc)
    for username in ("Maryna", "taras"):
        if not auth.users.by_username(username):
            auth.register(username, "demo123")
    owner = auth.users.by_username("Maryna")
    for name, data, created, modified in DEMO:
        files.upload(owner["id"], "Maryna", name, data, now=t0 + timedelta(minutes=created))
        if modified != created:
            files.upload(owner["id"], "Maryna", name, data + b"\n", now=t0 + timedelta(minutes=modified))
    print(f"Seeded {len(DEMO)} files into {data_dir} (user Maryna / demo123)")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else str(ROOT / "data" / "demo"))
