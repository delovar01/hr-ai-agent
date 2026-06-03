"""Generate QR code for Konovalov's screencast link.

Когда Коновалов пришлёт ссылку на Яндекс.Диск с записью работы продукта,
Стёпа или Кирилл запускают этот скрипт с реальной ссылкой:

    python scripts/make_video_qr.py "https://disk.yandex.ru/i/REAL_LINK"

Скрипт перепишет `docs/qr_codes/video_qr.png`, который Кирилл вставит на
последний слайд презентации.
"""
from __future__ import annotations

import sys
from pathlib import Path

import qrcode


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: python scripts/make_video_qr.py <video_url>")
        return 2
    url = sys.argv[1]
    out_dir = Path(__file__).resolve().parents[1] / "docs" / "qr_codes"
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / "video_qr.png"
    qrcode.make(url).save(path)
    print(f"QR saved: {path}")
    print(f"URL: {url}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
