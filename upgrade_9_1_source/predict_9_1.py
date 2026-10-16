# -*- coding: utf-8 -*-
"""Dự đoán tòa mới: chỉ thứ/buổi/tiết; địa điểm đã có lịch sử: dùng mô hình gốc."""
import json
from pathlib import Path
from functools import lru_cache

import pandas as pd
from predict import predict as predict_goc
from prediction_engine import single_query, history_scores

ROOT = Path(__file__).resolve().parent
META = json.loads((ROOT / 'model_metadata.json').read_text(encoding='utf-8'))

@lru_cache(maxsize=2)
def history(mode):
    path = ROOT / META[mode]['train_file']
    return pd.read_csv(path, encoding='utf-8-sig')


def predict(thu, buoi, phong, tiet_bat_dau=None, tiet_ket_thuc=None, top_k=3):
    q = single_query(thu, buoi, phong, tiet_bat_dau, tiet_ket_thuc)
    toa = str(q.iloc[0]['toa_nha']).upper()
    advanced = tiet_bat_dau is not None
    mode = 'advanced' if advanced else 'basic'
    hist = history(mode)
    toa_da_biet = set(hist['toa_nha'].astype(str).str.upper())

    # Tòa K chỉ bắt đầu từ HK1 2026-2027: không có lịch sử phòng K trong train cũ.
    # Với bất kỳ tòa mới nào, tuyệt đối không suy diễn vị trí từ G501 -> K501.
    if toa in toa_da_biet or toa == 'ONLINE':
        result = predict_goc(thu, buoi, phong, tiet_bat_dau, tiet_ket_thuc, top_k)
        result['che_do'] = 'thoi_gian_va_dia_diem_da_biet'
        result['toa_moi_chua_co_lich_su'] = False
        return result

    cfg = META[mode]
    if cfg.get('family') != 'History':
        raise RuntimeError('Chế độ fallback này yêu cầu Historical Matching.')
    weights = dict(cfg['weights'])
    # BỎ các yếu tố không có bằng chứng lịch sử ở tòa mới.
    weights.update(building=0.0, floor=0.0, room=0.0)
    teachers, scores, support = history_scores(hist, q, weights, advanced)
    if len(teachers) == 0:
        return dict(ket_qua=[], model='History_TimeOnly_ColdStart',
                    canh_bao='Không có lịch sử đủ dùng', thong_bao='Không có kết quả',
                    du_doan_co_co_so_kiem_dinh=False)
    # Khi không còn tín hiệu địa điểm, nhiều giảng viên có thể đồng điểm.
    # Xếp phụ theo số ca trùng thứ/buổi, rồi theo tên để ổn định,
    # nhưng không xem thứ tự phụ là bằng chứng chắc chắn về phân công.
    n_classes = hist['giang_vien'].value_counts().to_dict()
    rank_all = sorted(range(len(teachers)), key=lambda i: (
        -float(scores[0,i]), -int(support[0,i]),
        -int(n_classes.get(str(teachers[i]), 0)), str(teachers[i])))
    ranking = rank_all[:max(1, min(int(top_k), len(teachers)))]
    maxscore = float(scores[0].max())
    ties = [i for i in rank_all if abs(float(scores[0,i]) - maxscore) < 1e-9]
    result = {
        'ket_qua': [
            dict(giang_vien=str(teachers[i]), diem_xep_hang=float(scores[0,i]),
                 so_ca_lich_su_trung_thu_buoi=int(support[0,i]))
            for i in ranking
        ],
        'so_giang_vien_dong_diem_cao_nhat': len(ties),
        'giang_vien_dong_diem_cao_nhat': [
            dict(giang_vien=str(teachers[i]), diem_xep_hang=float(scores[0,i]),
                 so_ca_lich_su_trung_thu_buoi=int(support[0,i])) for i in ties
        ],
        'model': 'History_TimeOnly_ColdStart_' + mode,
        'che_do': 'chi_thoi_gian_toa_moi',
        'toa_moi_chua_co_lich_su': True,
        'du_doan_co_co_so_kiem_dinh': False,
        'thong_bao': 'Tòa ' + toa + ' chưa có lịch sử trong Train; chỉ xếp hạng theo thứ, buổi' +
                     (' và tiết học.' if advanced else '.') +
                     (' Có ' + str(len(ties)) + ' giảng viên đồng điểm cao nhất; Top 3 chỉ là ba người xếp đầu theo quy tắc phụ.'
                      if len(ties) > int(top_k) else ''),
        'canh_bao': 'Tòa K chỉ mới sử dụng từ HK1 2026-2027. Không có cơ sở nhận diện '
                    'thói quen phòng/tầng K từ các học kỳ cũ. Kết quả chỉ tham khảo; '
                    'điểm xếp hạng không phải xác suất, không phải lịch phân công chính thức.'
    }
    return result

if __name__ == '__main__':
    print(json.dumps(predict(5,'Sáng','K502'),ensure_ascii=False,indent=2))
