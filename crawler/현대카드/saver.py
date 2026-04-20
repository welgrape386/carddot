"""
saver.py - CSV 저장
append_csv: 파일 없으면 헤더 포함 신규 생성 / 있으면 append
"""

import csv
import os


def append_csv(filepath: str, rows: list, fieldnames: list):
    """
    rows: list of dict
    없으면 헤더 포함 신규 생성, 있으면 append
    """
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    file_exists = os.path.isfile(filepath)

    with open(filepath, "a", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if not file_exists:
            writer.writeheader()
        writer.writerows(rows)

    print(f"  저장 완료: {filepath} ({len(rows)}행 추가)")
