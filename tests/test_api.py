from fastapi.testclient import TestClient

from app.main import app
from model.predict_9_1 import predict


client = TestClient(app)


def post_predict(**overrides):
    payload = {
        "thu": 5,
        "buoi": "Sáng",
        "phong": "G502",
        "tiet_bat_dau": None,
        "tiet_ket_thuc": None,
    }
    payload.update(overrides)
    return client.post("/api/predict", json=payload)


def test_health_and_home():
    assert client.get("/api/health").json()["status"] == "ok"
    page = client.get("/")
    assert page.status_code == 200
    assert "VAU Teacher Predictor" in page.text


def test_basic_prediction_matches_step_9_1_function_and_keeps_original_result():
    direct = predict(thu=5, buoi="Sáng", phong="G502", top_k=3)
    response = post_predict()
    assert response.status_code == 200
    data = response.json()
    assert data["model"] == direct["model"]
    assert data["che_do"] == "thoi_gian_va_dia_diem_da_biet"
    assert data["toa_moi_chua_co_lich_su"] is False
    assert data["thong_bao"] == direct["thong_bao"]
    assert data["canh_bao"] == direct["canh_bao"]
    for api_item, direct_item in zip(data["ket_qua"], direct["ket_qua"]):
        assert api_item["giang_vien"] == direct_item["giang_vien"]
        assert api_item["diem_xep_hang"] == direct_item["diem_xep_hang"]
        assert (
            api_item["so_ca_lich_su_trung_thu_buoi"]
            == direct_item["so_ca_lich_su_trung_thu_buoi"]
        )
        assert api_item["giai_thich"]["so_ca_cung_thu_buoi"] == direct_item[
            "so_ca_lich_su_trung_thu_buoi"
        ]


def test_advanced_prediction_uses_periods():
    response = post_predict(phong="G501", tiet_bat_dau=1, tiet_ket_thuc=5)
    assert response.status_code == 200
    data = response.json()
    assert data["model"] == "History_time_strong_advanced_goc"
    assert len(data["ket_qua"]) == 3


def test_k502_uses_cold_start_and_returns_all_eight_ties():
    direct = predict(thu=5, buoi="Sáng", phong="K502", top_k=3)
    response = post_predict(phong="K502")
    assert response.status_code == 200
    data = response.json()
    assert data["model"] == "History_TimeOnly_ColdStart_basic"
    assert data["che_do"] == "chi_thoi_gian_toa_moi"
    assert data["toa_moi_chua_co_lich_su"] is True
    assert data["so_giang_vien_dong_diem_cao_nhat"] == 8
    assert len(data["giang_vien_dong_diem_cao_nhat"]) == 8
    assert data["giang_vien_dong_diem_cao_nhat"] == direct[
        "giang_vien_dong_diem_cao_nhat"
    ]
    assert [item["giang_vien"] for item in data["ket_qua"]] == [
        item["giang_vien"] for item in direct["ket_qua"]
    ]
    assert all(item["diem_xep_hang"] == 9.7 for item in data["ket_qua"])


def test_k501_with_periods_uses_advanced_cold_start():
    direct = predict(
        thu=5,
        buoi="Sáng",
        phong="K501",
        tiet_bat_dau=1,
        tiet_ket_thuc=5,
        top_k=3,
    )
    response = post_predict(phong="K501", tiet_bat_dau=1, tiet_ket_thuc=5)
    assert response.status_code == 200
    data = response.json()
    assert data["model"] == "History_TimeOnly_ColdStart_advanced"
    assert data["so_giang_vien_dong_diem_cao_nhat"] == 5
    assert data["ket_qua"][0]["diem_xep_hang"] == direct["ket_qua"][0][
        "diem_xep_hang"
    ]
    assert data["ket_qua"][0]["giai_thich"][
        "co_su_dung_tiet_de_xep_hang"
    ] is True


def test_other_unknown_building_is_named_in_warning():
    response = post_predict(phong="Z502")
    assert response.status_code == 200
    data = response.json()
    assert "Tòa Z" in data["thong_bao"]
    assert "Tòa Z" in data["canh_bao"]
    assert "Tòa K chỉ mới" not in data["canh_bao"]


def test_online_room_has_no_physical_floor_explanation():
    response = post_predict(phong="Online18")
    assert response.status_code == 200
    for item in response.json()["ket_qua"]:
        explanation = item["giai_thich"]
        assert explanation["la_phong_online"] is True
        assert explanation["so_ca_cung_toa_nha"] is None
        assert explanation["so_ca_cung_tang"] is None


def test_missing_room_is_rejected():
    response = client.post("/api/predict", json={"thu": 5, "buoi": "Sáng"})
    assert response.status_code == 422
    assert "phòng" in response.json()["detail"].lower()


def test_only_one_period_is_rejected():
    response = post_predict(tiet_bat_dau=1)
    assert response.status_code == 422
    assert "cả tiết bắt đầu" in response.json()["detail"].lower()


def test_invalid_room_is_rejected():
    response = post_predict(phong="phong ???")
    assert response.status_code == 422
    assert "phòng không hợp lệ" in response.json()["detail"].lower()


def test_invalid_period_range_is_rejected():
    response = post_predict(tiet_bat_dau=8, tiet_ket_thuc=3)
    assert response.status_code == 422
    assert "nhỏ hơn hoặc bằng" in response.json()["detail"].lower()


def test_out_of_range_period_is_rejected():
    response = post_predict(tiet_bat_dau=0, tiet_ket_thuc=3)
    assert response.status_code == 422
    assert "phạm vi" in response.json()["detail"].lower()


def test_metadata_comes_from_saved_reports():
    response = client.get("/api/metadata")
    assert response.status_code == 200
    data = response.json()
    assert data["version"] == "9.1"
    assert data["models"]["basic"]["validation"]["rows"] == 172
    assert data["models"]["basic"]["test_reference"]["split"] == "Test_tham_khao"
    assert "G502" in data["phong_goi_y"]
    assert "K502" in data["phong_cold_start_goi_y"]
    assert data["cold_start"]["so_ca_train_K"] == 0
