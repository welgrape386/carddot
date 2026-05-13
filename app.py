"""
카드 혜택 뷰어 (app.py)
실행: python app.py
접속: http://localhost:5000
"""

import os
from flask import Flask, jsonify, request
from benefit_engine import BenefitEngine

# index.html이 있는 폴더를 static으로 지정
BASE = os.path.dirname(os.path.abspath(__file__))
app = Flask(__name__, static_folder=BASE, static_url_path="")

CARDS = {
    "samsung": [
        ("AAP1731",          "iD ON 카드"),
        ("AAP1483",          "taptap O"),
        ("AAP1452",          "MILEAGE PLATINUM"),
        ("ABP1383",          "CASHBACK 체크"),
        ("ABP1384",          "POINT 체크"),
        ("ABP1689",          "국민행복 V2 체크"),
    ],
    "shinhan": [
        ("1228407_2207", "Point Plan+"),
        ("1226113_2207", "Point Plan"),
        ("1227751_2207", "SOL트래블"),
        ("1225714_2206", "SOL트래블 체크"),
        ("1226114_2206", "Point Plan 체크"),
        ("1196867_2206", "Hey Young 체크"),
    ],
    "hyundae": [
        ("ME4",    "현대카드M"),
        ("XPE4",   "현대카드X"),
        ("MZROE3", "현대카드ZERO Edition3(포인트형)"),
        ("CCM",    "현대카드 체크(포인트형)"),
        ("CCD",    "현대카드 체크(캐시백형)"),
        ("CCA",    "현대카드 체크(Apple Pay Rewards)"),
    ],
}

_engines = {}

def get_engine(company):
    if company not in _engines:
        _engines[company] = BenefitEngine(
            os.path.join(BASE, f"{company}_benefit.csv"),
            os.path.join(BASE, f"{company}_info.csv"),
        )
    return _engines[company]

@app.route("/")
def index():
    return app.send_static_file("index.html")

@app.route("/api/cards")
def api_cards():
    from flask import jsonify
    return jsonify(CARDS)

@app.route("/api/summary/<company>/<card_id>")
def api_summary(company, card_id):
    from flask import jsonify
    try:
        df = get_engine(company).get_card_summary(card_id)
        return jsonify(df.fillna("-").to_dict(orient="records"))
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route("/api/benefits/<company>/<card_id>")
def api_benefits(company, card_id):
    from flask import jsonify
    try:
        df = get_engine(company).get_card_benefits(card_id)
        return jsonify(df.fillna("-").to_dict(orient="records"))
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route("/api/compare")
def api_compare():
    from flask import jsonify
    items = request.args.getlist("card")
    result = {}
    for item in items:
        try:
            company, card_id = item.split(":", 1)
            df = get_engine(company).get_card_benefits(card_id)
            result[item] = df.fillna("-").to_dict(orient="records")
        except Exception as e:
            result[item] = {"error": str(e)}
    return jsonify(result)

if __name__ == "__main__":
    print(f"\n🚀  카드 혜택 뷰어  →  http://localhost:5000")
    print(f"📁  폴더: {BASE}\n")
    app.run(debug=True, port=5000)