from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from model.predict_9_1 import predict

from .services import enrich_prediction, public_metadata


APP_DIR = Path(__file__).resolve().parent
STATIC_DIR = APP_DIR / "static"
TEMPLATE_DIR = APP_DIR / "templates"

app = FastAPI(
    title="VAU Teacher Predictor API",
    description="Dự đoán tham khảo Bước 9.1, có hỗ trợ cold-start cho tòa mới.",
    version="1.1.0",
)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


class PredictionRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    thu: int = Field(ge=2, le=8)
    buoi: str = Field(min_length=1)
    phong: str = Field(min_length=1)
    tiet_bat_dau: int | None = None
    tiet_ket_thuc: int | None = None

    @field_validator("buoi")
    @classmethod
    def validate_buoi(cls, value: str) -> str:
        allowed = {"sáng": "Sáng", "chiều": "Chiều", "tối": "Tối"}
        normalized = allowed.get(value.lower())
        if not normalized:
            raise ValueError("Buổi học phải là Sáng, Chiều hoặc Tối.")
        return normalized

    @model_validator(mode="after")
    def validate_periods(self) -> "PredictionRequest":
        has_start = self.tiet_bat_dau is not None
        has_end = self.tiet_ket_thuc is not None
        if has_start != has_end:
            raise ValueError("Nếu nhập tiết học, vui lòng nhập cả tiết bắt đầu và tiết kết thúc.")
        if has_start:
            assert self.tiet_bat_dau is not None and self.tiet_ket_thuc is not None
            if not (1 <= self.tiet_bat_dau <= 20 and 1 <= self.tiet_ket_thuc <= 20):
                raise ValueError("Tiết học phải nằm trong phạm vi từ 1 đến 20.")
            if self.tiet_bat_dau > self.tiet_ket_thuc:
                raise ValueError("Tiết bắt đầu phải nhỏ hơn hoặc bằng tiết kết thúc.")
        return self


def validation_message(errors: list[dict[str, Any]]) -> str:
    first = errors[0] if errors else {}
    field = str(first.get("loc", [""])[-1])
    message = str(first.get("msg", "Dữ liệu không hợp lệ."))
    custom = {
        "thu": "Vui lòng chọn thứ hợp lệ từ Thứ 2 đến Chủ nhật.",
        "buoi": "Vui lòng chọn buổi học: Sáng, Chiều hoặc Tối.",
        "phong": "Vui lòng nhập phòng học.",
        "tiet_bat_dau": "Tiết bắt đầu phải là số nguyên hợp lệ.",
        "tiet_ket_thuc": "Tiết kết thúc phải là số nguyên hợp lệ.",
    }
    if "Value error," in message:
        return message.split("Value error,", 1)[1].strip()
    return custom.get(field, "Dữ liệu gửi lên không hợp lệ. Vui lòng kiểm tra lại.")


@app.exception_handler(RequestValidationError)
async def request_validation_handler(
    _request: Request, exc: RequestValidationError
) -> JSONResponse:
    return JSONResponse(status_code=422, content={"detail": validation_message(exc.errors())})


@app.get("/", include_in_schema=False)
def home() -> FileResponse:
    return FileResponse(TEMPLATE_DIR / "index.html")


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "VAU Teacher Predictor"}


@app.get("/api/metadata")
def metadata() -> dict[str, Any]:
    try:
        return public_metadata()
    except Exception as exc:
        raise HTTPException(
            status_code=500, detail="Không thể đọc thông tin mô hình."
        ) from exc


@app.post("/api/predict")
def make_prediction(payload: PredictionRequest) -> dict[str, Any]:
    try:
        result = predict(
            thu=payload.thu,
            buoi=payload.buoi,
            phong=payload.phong,
            tiet_bat_dau=payload.tiet_bat_dau,
            tiet_ket_thuc=payload.tiet_ket_thuc,
            top_k=3,
        )
        return enrich_prediction(
            result,
            thu=payload.thu,
            buoi=payload.buoi,
            phong=payload.phong,
            tiet_bat_dau=payload.tiet_bat_dau,
            tiet_ket_thuc=payload.tiet_ket_thuc,
        )
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail="Máy chủ chưa thể thực hiện dự đoán. Vui lòng thử lại.",
        ) from exc
