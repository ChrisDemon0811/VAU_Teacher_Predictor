import importlib.util
from pathlib import Path


APP_ROOT = Path(__file__).resolve().parents[1]
PREDICTOR_PATH = APP_ROOT / "model" / "predictor.py"
SPEC = importlib.util.spec_from_file_location("streamlit_hk2_predictor", PREDICTOR_PATH)
assert SPEC and SPEC.loader
PREDICTOR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PREDICTOR)
load_assets = PREDICTOR.load_assets
predict = PREDICTOR.predict
parse_room = PREDICTOR.parse_room


def test_final_training_data_has_740_rows_and_no_target_semester():
    history, _config, report, _catalog = load_assets()
    assert len(history) == 740
    assert report["final_train_rows"] == 740
    target = history[
        (history["nam_hoc"].astype(str) == "2026-2027")
        & (history["hoc_ky"].astype(str) == "2")
    ]
    assert target.empty


def test_g502_without_course_keeps_history_ranking():
    result = predict(5, "Sáng", "G502")
    assert result["model"] == "HistoryHK2_2026_2027_course_optional"
    assert result["so_ca_du_lieu_train"] == 740
    assert result["ket_qua"][0]["giang_vien"] == "Nguyễn Thị Ngọc Thanh"
    assert result["ket_qua"][0]["diem_xep_hang"] == 11.282
    assert result["co_su_dung_mon_hoc"] is False


def test_known_course_is_used_and_unknown_course_falls_back():
    _history, _config, _report, catalog = load_assets()
    known = str(catalog.iloc[0]["ten_mon"])
    with_course = predict(5, "Sáng", "G502", ten_mon=known)
    unknown = predict(5, "Sáng", "G502", ten_mon="Môn chưa tồn tại 999")
    assert with_course["mon_hoc_co_lich_su"] is True
    assert with_course["co_su_dung_mon_hoc"] is True
    assert any(item["da_tung_day_mon"] for item in with_course["ket_qua"])
    assert unknown["mon_hoc_co_lich_su"] is False
    assert unknown["co_su_dung_mon_hoc"] is False
    assert "Không tìm được môn này" in unknown["canh_bao"]


def test_k502_uses_trained_k_history():
    result = predict(5, "Sáng", "K502")
    assert result["toa_moi_chua_co_lich_su"] is False
    assert result["che_do"] == "thoi_gian_va_dia_diem"
    assert result["toa_nha"] == "K"
    assert "canh_bao_tang_tret" not in result
    assert result["ket_qua"][0]["giang_vien"] == "Nguyễn Thái Sơn"


def test_ground_floor_k_rooms_use_building_history_without_floor_history():
    history, _config, _report, catalog = load_assets()
    assert history[(history["toa_nha"] == "K") & (history["tang"] == 0)].empty
    known_subject = str(catalog.iloc[0]["ten_mon"])
    warning = "Chưa có dữ liệu lịch sử tầng trệt tòa K; kết quả chỉ mang tính tham khảo."

    for room, number in (("K02", 2), ("K04", 4)):
        assert parse_room(room) == (room, "K", 0, number)
        result = predict(5, "Sáng", room, 1, 5, known_subject)
        assert len(result["ket_qua"]) == 3
        assert result["so_ca_du_lieu_train"] == 740
        assert result["toa_nha"] == "K"
        assert result["che_do"] == "thoi_gian_va_dia_diem"
        assert result["canh_bao_tang_tret"] == warning
        assert warning in result["canh_bao"]
        assert result["co_su_dung_mon_hoc"] is True
        assert any(item["so_ca_trung_toa_nha"] > 0 for item in result["ket_qua"])
        assert all(item["so_ca_trung_tang"] == 0 for item in result["ket_qua"])
        assert all(item["so_ca_trung_phong"] == 0 for item in result["ket_qua"])


def test_room_parser_keeps_existing_buildings_and_online():
    assert parse_room("G502") == ("G502", "G", 5, 2)
    assert parse_room("K101") == ("K101", "K", 1, 1)
    assert parse_room("K502") == ("K502", "K", 5, 2)
    assert parse_room("K1002") == ("K1002", "K", 10, 2)
    assert parse_room("Online18") == ("ONLINE", "ONLINE", -1, -1)


def test_online18_has_no_physical_location_signal():
    result = predict(5, "Sáng", "Online18")
    assert result["che_do"] == "chi_thoi_gian_online"
    assert result["toa_nha"] == "ONLINE"
    assert all(item["so_ca_trung_toa_nha"] == 0 for item in result["ket_qua"])
    assert all(item["so_ca_trung_tang"] == 0 for item in result["ket_qua"])
    assert all(item["so_ca_trung_phong"] == 0 for item in result["ket_qua"])


def test_input_validation():
    for room in ("", "phòng ???"):
        try:
            predict(5, "Sáng", room)
        except ValueError as exc:
            assert "Phòng không hợp lệ" in str(exc)
        else:
            raise AssertionError("Phòng không hợp lệ phải bị từ chối")

    try:
        predict(5, "Sáng", "G502", 8, 3)
    except ValueError as exc:
        assert "Tiết" in str(exc)
    else:
        raise AssertionError("Khoảng tiết không hợp lệ phải bị từ chối")
