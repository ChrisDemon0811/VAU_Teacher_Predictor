from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

import pandas as pd

from model.prediction_engine import single_query


ROOT = Path(__file__).resolve().parents[1]
MODEL_DIR = ROOT / "model"


@lru_cache(maxsize=1)
def load_metadata() -> dict[str, Any]:
    return json.loads((MODEL_DIR / "model_metadata.json").read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def load_report() -> dict[str, Any]:
    return json.loads((MODEL_DIR / "bao_cao_buoc9.json").read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def load_cold_start_report() -> dict[str, Any]:
    return json.loads(
        (MODEL_DIR / "bao_cao_9_1_sua.json").read_text(encoding="utf-8")
    )


@lru_cache(maxsize=2)
def load_history(filename: str) -> pd.DataFrame:
    return pd.read_csv(MODEL_DIR / filename, encoding="utf-8-sig")


def public_metadata() -> dict[str, Any]:
    metadata = load_metadata()
    report = load_report()
    cold_start_report = load_cold_start_report()
    basic_history = load_history(metadata["basic"]["train_file"])
    rooms = sorted(
        str(room)
        for room in basic_history["phong"].dropna().unique()
        if str(room).strip()
    )

    def public_model(name: str) -> dict[str, Any]:
        config = metadata[name]
        return {
            "name": config["name"],
            "family": config["family"],
            "validation": config["validation"],
            "test_reference": config["test_reference"],
        }

    return {
        "version": "9.1",
        "models": {
            "basic": public_model("basic"),
            "advanced": public_model("advanced"),
        },
        "dataset": {
            "input_train": report["input_train"],
            "recovered_online": report["recovered_online"],
            "new_train": report["new_train"],
            "validation": report["validation"],
            "test": report["test"],
        },
        "warning": metadata["warning"],
        "caveat": report["caveat"],
        "phong_goi_y": rooms,
        "phong_cold_start_goi_y": ["K501", "K502", "K503"],
        "cold_start": {
            "ket_luan": cold_start_report["ket_luan"],
            "so_ca_train_K": cold_start_report["so_ca_train_K"],
            "cac_toa_train": cold_start_report["cac_toa_train"],
            "khong_dung_test_de_train": cold_start_report[
                "khong_dung_test_de_train"
            ],
            "so_giang_vien_dong_diem_cao_nhat_K502": cold_start_report[
                "so_giang_vien_dong_diem_cao_nhat_K502"
            ],
        },
        "official_schedule_url": "https://pdt.vau.edu.vn/tra-cuu-thoi-khoa-bieu",
    }


def enrich_prediction(
    result: dict[str, Any],
    *,
    thu: int,
    buoi: str,
    phong: str,
    tiet_bat_dau: int | None,
    tiet_ket_thuc: int | None,
) -> dict[str, Any]:
    """Bổ sung giải thích từ CSV, không can thiệp điểm hay thứ hạng gốc."""
    advanced = tiet_bat_dau is not None
    config = load_metadata()["advanced" if advanced else "basic"]
    history = load_history(config["train_file"])
    query = single_query(thu, buoi, phong, tiet_bat_dau, tiet_ket_thuc).iloc[0]
    is_cold_start = bool(result.get("toa_moi_chua_co_lich_su", False))

    for ranked in result["ket_qua"]:
        teacher_rows = history[history["giang_vien"] == ranked["giang_vien"]]
        same_time = teacher_rows[
            (teacher_rows["thu"] == int(query["thu"]))
            & (teacher_rows["buoi"] == query["buoi"])
        ]

        terms = sorted(
            {
                f"{row.nam_hoc} · HK{row.hoc_ky}"
                for row in teacher_rows[["nam_hoc", "hoc_ky"]].itertuples(index=False)
            }
        )
        rooms = sorted(
            {
                str(value)
                for value in same_time["phong"].dropna().tolist()
                if str(value).strip()
            }
        )

        is_online = query["toa_nha"] == "ONLINE"
        same_building_count: int | None = None
        same_floor_count: int | None = None
        if not is_online:
            same_building = teacher_rows[teacher_rows["toa_nha"] == query["toa_nha"]]
            same_building_count = int(len(same_building))
            same_floor_count = int(
                len(same_building[same_building["tang"] == int(query["tang"])])
            )

        ranked["giai_thich"] = {
            "so_ca_cung_thu_buoi": int(len(same_time)),
            "phong_da_day_cung_thu_buoi": rooms,
            "hoc_ky_co_du_lieu": terms,
            "toa_nha": str(query["toa_nha"]),
            "la_phong_online": bool(is_online),
            "la_toa_moi": is_cold_start,
            "co_su_dung_vi_tri_de_xep_hang": bool(
                not is_cold_start and not is_online
            ),
            "co_su_dung_tiet_de_xep_hang": bool(advanced),
            "so_ca_cung_toa_nha": same_building_count,
            "so_ca_cung_tang": same_floor_count,
        }

    return result
