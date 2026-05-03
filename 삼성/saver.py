"""
saver.py - 삼성카드 크롤링 결과 CSV 저장
"""

import csv
import os


def save_rows_to_csv(rows: list[dict], filename: str):
    """rows를 CSV에 append 저장 (헤더는 파일이 없을 때만 작성)"""
    if not rows:
        return

    file_exists = os.path.exists(filename)

    with open(filename, "a", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        if not file_exists:
            writer.writeheader()
        writer.writerows(rows)

    print(f"  저장 완료: {filename} ({len(rows)}행)")
