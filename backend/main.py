from pathlib import Path
import json
import os
import pickle
from functools import lru_cache
from typing import List, Optional

import numpy as np
import pandas as pd
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from openai import OpenAI
from pydantic import BaseModel

from preprocess import build_model_input

BASE_DIR = Path(__file__).resolve().parent
PROJECT_DIR = BASE_DIR.parent
MODEL_PATHS = [
    BASE_DIR / "models" / "xgb_quantile_kfte_tuned_models.pkl",
    BASE_DIR / "models" / "xgb_quantile_models.pkl",
]
FEATURE_PATHS = [
    BASE_DIR / "models" / "kfte_feature_columns.pkl",
    BASE_DIR / "models" / "model_features.pkl",
]
ENCODING_PATH = BASE_DIR / "models" / "kfte_encoding_map.pkl"


def load_env_file():
    env_paths = [
        PROJECT_DIR / ".env.local",
        PROJECT_DIR / ".env",
        BASE_DIR / ".env.local",
        BASE_DIR / ".env",
    ]

    for env_path in env_paths:
        if not env_path.exists():
            continue

        for raw_line in env_path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue

            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")

            if key and key not in os.environ:
                os.environ[key] = value


load_env_file()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
openai_client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class PredictRequest(BaseModel):
    manufacturer: str
    model: str
    trim: str = ""
    year: str
    displacement: str
    fuel: str
    transmission: str
    vehicleClass: str
    seats: str
    color: str
    mileage: str
    accident: str
    exchangeCount: str = "없음"
    paintCount: str = "없음"
    insuranceCount: str = "없음"
    corrosion: str = "없음"
    options: list[str] = []


def resolve_existing_path(paths: list[Path]) -> Path:
    for path in paths:
        if path.exists():
            return path
    raise FileNotFoundError(f"아티팩트를 찾을 수 없습니다: {paths}")


@lru_cache(maxsize=1)
def load_artifacts():
    model_path = resolve_existing_path(MODEL_PATHS)
    feature_path = resolve_existing_path(FEATURE_PATHS)

    with open(model_path, "rb") as model_file:
        models = pickle.load(model_file)

    with open(feature_path, "rb") as feature_file:
        model_features = pickle.load(feature_file)

    model_encoding_map = {}
    if ENCODING_PATH.exists():
        with open(ENCODING_PATH, "rb") as encoding_file:
            model_encoding_map = pickle.load(encoding_file)

    return models, model_features, model_encoding_map


def get_quantile_model(models, quantile: float):
    if isinstance(models, dict):
        for candidate in (quantile, str(quantile)):
            if candidate in models:
                return models[candidate]

        for key, model in models.items():
            try:
                if abs(float(key) - quantile) < 1e-9:
                    return model
            except (TypeError, ValueError):
                continue

        raise KeyError(f"해당 분위수 모델을 찾을 수 없습니다: {quantile}")

    if isinstance(models, (list, tuple)) and len(models) >= 3:
        if quantile <= 0.05:
            return models[0]
        if quantile >= 0.95:
            return models[-1]
        return models[len(models) // 2]

    raise TypeError("지원하지 않는 모델 아티팩트 형식입니다.")


def decode_prediction(raw_prediction: float) -> float:
    return float(np.expm1(raw_prediction)) if raw_prediction < 20 else float(raw_prediction)


def get_base_margin(row: dict) -> Optional[List[float]]:
    if "모델_encoded" not in row:
        return None
    return [float(row["모델_encoded"])]


def get_margin_rate(q50: float) -> float:
    if q50 < 1500:
        return 0.08
    if q50 < 3000:
        return 0.07
    if q50 < 5000:
        return 0.06
    return 0.05


def get_fixed_cost() -> int:
    return 25


def get_fast_discount(q50: float) -> int:
    return int(min(max(q50 * 0.01, 15), 40))


def get_trust_discount(q50: float) -> int:
    return int(min(max(q50 * 0.005, 10), 30))


def adjust_to_c2c_prices(q05: float, q50: float, q95: float):
    fixed_cost = get_fixed_cost()
    margin_rate = get_margin_rate(q50)
    fast_discount = get_fast_discount(q50)
    trust_discount = get_trust_discount(q50)

    dealer_component = q50 * margin_rate

    fair_price = q50 - ((fixed_cost + dealer_component) / 2)
    fast_formula = q50 - (fixed_cost + dealer_component) - fast_discount
    high_formula = q50 - trust_discount

    fast_price = min(q05, fast_formula)
    high_price = min(q95, high_formula)

    fast_price = max(fast_price, 0)
    fair_price = max(fair_price, 0)
    high_price = max(high_price, 0)

    if fast_price > fair_price:
        fast_price = max(fair_price - 10, 0)

    if high_price < fair_price:
        high_price = fair_price

    return {
        "fast": round(fast_price, 0),
        "fair": round(fair_price, 0),
        "high": round(high_price, 0),
        "fixedCost": fixed_cost,
        "marginRate": round(margin_rate, 4),
        "fastDiscount": fast_discount,
        "trustDiscount": trust_discount,
    }


def generate_price_explanation(
    form_data: dict, fast_price: float, fair_price: float, high_price: float
) -> dict:
    default_result = {
        "summary": "입력한 차량 조건을 바탕으로 예상 판매 가격대를 계산했습니다.",
        "detail": "연식, 주행거리, 사고 이력, 옵션 수를 함께 반영해 가격 범위를 구성했습니다.",
        "tip": "빠르게 판매하려면 빠른 판매가를, 여유가 있다면 적정 판매가부터 시작해 보세요.",
        "source": "fallback",
    }

    if not openai_client:
        return default_result

    accident_text = (
        "사고 이력 있음"
        if "사고" in str(form_data.get("accident", ""))
        else "무사고"
    )
    option_count = len(form_data.get("options", []))

    prompt = f"""
다음 중고차 가격 예측 결과를 바탕으로 JSON만 출력해 주세요.

출력 형식:
{{
  "summary": "한 문장 요약",
  "detail": "2~3문장 설명",
  "tip": "판매 팁 한 문장"
}}

차량 정보:
- 제조사: {form_data.get("manufacturer")}
- 모델: {form_data.get("model")}
- 트림: {form_data.get("trim")}
- 연식: {form_data.get("year")}
- 배기량: {form_data.get("displacement")}cc
- 연료: {form_data.get("fuel")}
- 변속기: {form_data.get("transmission")}
- 차종: {form_data.get("vehicleClass")}
- 좌석 수: {form_data.get("seats")}
- 색상: {form_data.get("color")}
- 주행거리: {form_data.get("mileage")}km
- 사고 여부: {accident_text}
- 교환 부위 수: {form_data.get("exchangeCount")}
- 판금 부위 수: {form_data.get("paintCount")}
- 보험 이력: {form_data.get("insuranceCount")}
- 부식 여부: {form_data.get("corrosion")}
- 주요 옵션 수: {option_count}

예측 결과:
- 빠른 판매가: {round(fast_price)}만원
- 적정 판매가: {round(fair_price)}만원
- 기대 판매가: {round(high_price)}만원
"""

    try:
        response = openai_client.responses.create(
            model="gpt-4.1-mini",
            input=[
                {
                    "role": "system",
                    "content": "당신은 중고차 판매가 설명을 작성하는 도우미입니다. 반드시 JSON만 출력하세요.",
                },
                {
                    "role": "user",
                    "content": prompt,
                },
            ],
            max_output_tokens=300,
        )

        result = json.loads(response.output_text.strip())
        return {
            "summary": result.get("summary", default_result["summary"]),
            "detail": result.get("detail", default_result["detail"]),
            "tip": result.get("tip", default_result["tip"]),
            "source": "openai",
        }
    except Exception:
        return default_result

@app.get("/")
def root():
    return {"message": "backend is running"}

@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/predict")
def predict(req: PredictRequest):
    if req.fuel == "전기":
        raise HTTPException(status_code=400, detail="현재 전기차는 지원하지 않습니다.")

    try:
        models, model_features, model_encoding_map = load_artifacts()
        form_data = req.model_dump()

        row = build_model_input(form_data, model_features, model_encoding_map)
        x_input = pd.DataFrame([[row[col] for col in model_features]], columns=model_features)
        base_margin = get_base_margin(row)

        pred_fast = decode_prediction(
            get_quantile_model(models, 0.05).predict(x_input, base_margin=base_margin)[0]
        )
        pred_mid = decode_prediction(
            get_quantile_model(models, 0.5).predict(x_input, base_margin=base_margin)[0]
        )
        pred_high = decode_prediction(
            get_quantile_model(models, 0.95).predict(x_input, base_margin=base_margin)[0]
        )

        q05, q50, q95 = sorted([pred_fast, pred_mid, pred_high])
        adjusted = adjust_to_c2c_prices(q05, q50, q95)

        explanation = generate_price_explanation(
            form_data=form_data,
            fast_price=adjusted["fast"],
            fair_price=adjusted["fair"],
            high_price=adjusted["high"],
        )

        return {
            "fastPrice": adjusted["fast"],
            "fairPrice": adjusted["fair"],
            "highPrice": adjusted["high"],
            "pricingMeta": {
                "fixedCost": adjusted["fixedCost"],
                "marginRate": adjusted["marginRate"],
                "fastDiscount": adjusted["fastDiscount"],
                "trustDiscount": adjusted["trustDiscount"],
                "baseQ50": round(q50, 0),
            },
            "explanation": explanation,
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
