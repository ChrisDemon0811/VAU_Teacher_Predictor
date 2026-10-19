# -*- coding: utf-8 -*-
"""Historical Matching for future-semester teacher suggestions, not official assignments."""
from __future__ import annotations
import json, math, re, unicodedata
from functools import lru_cache
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent


def normalise_text(value):
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return ""
    s = unicodedata.normalize('NFD', str(value).strip().lower()).replace('đ', 'd')
    s = ''.join(c for c in s if not unicodedata.combining(c))
    return re.sub(r'[^a-z0-9]+', ' ', s).strip()


def parse_room(room):
    s = re.sub(r'\s+', '', str(room).upper().strip())
    if re.fullmatch(r'ONLINE[0-9A-Z]*', s):
        return 'ONLINE', 'ONLINE', -1, -1
    m = re.fullmatch(r'([A-Z]{1,3})[.\-]?(\d{2,4})([A-Z]?)', s)
    if not m:
        raise ValueError('Phòng không hợp lệ. Ví dụ: G502, K501, Online18')
    building, digits, suffix = m.groups()
    floor = int(digits[:-2] or '0')
    if not 0 <= floor <= 30:
        raise ValueError('Tầng phải nằm trong khoảng 0 đến 30')
    return building + digits + suffix, building, floor, int(digits[-2:])


def normalise_session(value):
    s = normalise_text(value)
    m = {'sang':'Sáng', 'chieu':'Chiều', 'toi':'Tối'}
    if s not in m:
        raise ValueError('Buổi chỉ được là Sáng, Chiều hoặc Tối')
    return m[s]


def normalise_day(value):
    s = normalise_text(value).replace('thu ', '').strip()
    if s in ('cn','chu nhat'):
        return 8
    try: v = int(s)
    except (ValueError,TypeError): v=-1
    if v not in range(2,9):
        raise ValueError('Thứ phải nằm trong khoảng 2–8 (8 = Chủ nhật)')
    return v


@lru_cache(maxsize=1)
def load_assets():
    history = pd.read_csv(ROOT / 'retrained_history.csv', encoding='utf-8-sig', dtype={'ma_lhp': str})
    config = json.loads((ROOT / 'config.json').read_text(encoding='utf-8'))
    report = json.loads((ROOT / 'report.json').read_text(encoding='utf-8'))
    catalog = pd.read_csv(ROOT / 'catalog_hk2_2025_2026.csv', encoding='utf-8-sig', dtype={'ma_mon': str})
    if 'mon_key' not in history:
        raise RuntimeError('Thiếu cột mon_key trong model/retrained_history.csv')
    return history, config, report, catalog


def rank_history(history:pd.DataFrame, query:dict, *, weights:dict, course_bonus:float=0., top_k:int=3):
    """Match lesson time; bonus from *prior* course-level teaching. Scores are not probabilities."""
    h=history
    if h.empty: return {'ket_qua':[], 'so_giang_vien_dong_diem_cao_nhat':0}
    day=(h['thu'].to_numpy(dtype=int)==query['thu'])
    session=(h['buoi'].to_numpy(dtype=str)==query['buoi'])
    same_time=day & session
    existing={str(x).upper() for x in h['toa_nha'].dropna().unique() if str(x).upper()!='ONLINE'}
    cold_start=query['toa_nha'] not in existing and query['toa_nha']!='ONLINE'
    physical=(h['toa_nha'].to_numpy(dtype=str)==query['toa_nha']) & (query['toa_nha']!='ONLINE') & (not cold_start)
    floor=physical & (h['tang'].to_numpy(dtype=int)==query['tang'])
    room=physical & (h['phong'].to_numpy(dtype=str)==query['phong'])
    score=(weights['day']*day + weights['session']*session + weights['joint']*same_time+
           weights['building']*physical + weights['floor']*floor + weights['room']*room).astype(float)
    if query['tiet_bat_dau'] is not None:
        overlap=np.maximum(0,np.minimum(h['tiet_ket_thuc'].to_numpy(dtype=int), query['tiet_ket_thuc']) -
                             np.maximum(h['tiet_bat_dau'].to_numpy(dtype=int), query['tiet_bat_dau']) + 1)
        dur=max(1,query['tiet_ket_thuc']-query['tiet_bat_dau']+1)
        score+=weights['period']*same_time*overlap/dur
    names=sorted(str(x) for x in h.giang_vien.dropna().unique())
    hn=h.giang_vien.to_numpy(dtype=str)
    cm=h.mon_key.fillna('').to_numpy(dtype=str)
    scores=[]
    for t in names:
        mask=(hn==t)
        v=np.sort(score[mask])[-min(3,int(mask.sum())):]
        s=0.82*float(v[-1])+0.18*float(np.mean(v))
        matched_course=bool(query.get('mon_key')) and np.any((cm == query.get('mon_key')) & mask)
        courses_count=len(set(h.loc[mask & (cm==query.get('mon_key','')),'class_group'].astype(str))) if matched_course else 0
        if matched_course: s += float(course_bonus)*min(1.5,math.sqrt(courses_count))
        scores.append(dict(giang_vien=t,diem_xep_hang=round(s,6),
                           so_ca_lich_su_trung_thu_buoi=int(same_time[mask].sum()),
                           so_ca_trung_toa_nha=int(physical[mask].sum()),
                           so_ca_trung_tang=int(floor[mask].sum()),
                           so_ca_trung_phong=int(room[mask].sum()),
                           so_nhom_lop_tung_day_mon=int(courses_count),
                           da_tung_day_mon=bool(matched_course),
                           so_ca_lich_su=int(mask.sum())))
    scores.sort(key=lambda x:(-x['diem_xep_hang'],-x['so_ca_lich_su_trung_thu_buoi'],
                               -x['so_nhom_lop_tung_day_mon'],-x['so_ca_lich_su'],x['giang_vien']))
    top = scores[:max(1,min(int(top_k),len(scores)))]
    maxscore=scores[0]['diem_xep_hang']
    ties=[x for x in scores if abs(x['diem_xep_hang']-maxscore)<1e-5]
    return {'ket_qua':top, 'so_giang_vien_dong_diem_cao_nhat':len(ties),
            'giang_vien_dong_diem_cao_nhat':ties if len(ties)>3 else [],
            'toa_moi_chua_co_lich_su':bool(cold_start),
            'che_do':'chi_thoi_gian_toa_moi' if cold_start else ('chi_thoi_gian_online' if query['toa_nha']=='ONLINE' else 'thoi_gian_va_dia_diem'),
            'co_su_dung_mon_hoc':bool(query.get('mon_key')) and (h.mon_key==query.get('mon_key')).any(),
            'so_ca_du_lieu_train':len(h),
            'toa_nha':query['toa_nha']}


def predict(thu,buoi,phong,tiet_bat_dau=None,tiet_ket_thuc=None,ten_mon=None,top_k=3):
    d=normalise_day(thu);s=normalise_session(buoi)
    room,building,floor,number=parse_room(phong)
    if (tiet_bat_dau is None) != (tiet_ket_thuc is None):
        raise ValueError('Nhập cả hai tiết hoặc bỏ trống cả hai')
    if tiet_bat_dau is not None:
        a,b=int(tiet_bat_dau),int(tiet_ket_thuc)
        if not(1<=a<=b<=20):raise ValueError('Tiết phải trong khoảng 1–20 và tiết bắt đầu không lớn hơn tiết kết thúc')
    else: a=b=None
    history,conf,report,catalog=load_assets()
    label=str(ten_mon or '').strip()
    # Do not hallucinate a course: only exact historical title (accent-insensitive) gets bonus.
    key=normalise_text(label)
    known=set(catalog['mon_key'].fillna('').astype(str).tolist())
    if key not in known: key=''
    query=dict(thu=d,buoi=s,phong=room,toa_nha=building,tang=floor,
               so_phong=number,tiet_bat_dau=a,tiet_ket_thuc=b,mon_key=key)
    result=rank_history(history,query,weights=conf['weights'],course_bonus=conf['course_bonus'],top_k=top_k)
    result['model']='HistoryHK2_2026_2027_course_optional'
    result['ten_mon']=label
    result['mon_hoc_co_lich_su']=bool(key)
    result['co_su_dung_mon_hoc']=bool(result.get('co_su_dung_mon_hoc'))
    warnings=['Điểm xếp hạng chỉ là tín hiệu so khớp lịch sử, không phải xác suất hoặc lịch phân công chính thức.']
    if not key and label: warnings.append('Không tìm được môn này trong dữ liệu HK2 2025–2026; hệ thống chỉ dùng thứ, buổi, tiết và phòng.')
    if result.get('toa_moi_chua_co_lich_su'):warnings.append('Tòa '+building+' chưa có lịch sử trong Train; kết quả không sử dụng trọng số tòa/tầng/phòng.')
    if building == 'K' and floor == 0 and history[(history['toa_nha'] == 'K') & (history['tang'] == 0)].empty:
        result['canh_bao_tang_tret'] = 'Chưa có dữ liệu lịch sử tầng trệt tòa K; kết quả chỉ mang tính tham khảo.'
        warnings.append(result['canh_bao_tang_tret'])
    if len(result.get('giang_vien_dong_diem_cao_nhat',[]))>3:warnings.append('Có '+str(result['so_giang_vien_dong_diem_cao_nhat'])+' giảng viên đồng điểm cao nhất.')
    result['canh_bao']=' '.join(warnings)
    result['thong_bao']='Dự đoán cho HK2 2026–2027, chỉ tham khảo.'
    return result
