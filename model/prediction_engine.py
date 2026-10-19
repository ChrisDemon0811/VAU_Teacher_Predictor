import re
import unicodedata
import numpy as np
import pandas as pd

CAT = ['thu','buoi','toa_nha','tang','phong','thu_buoi','toa_tang','thu_buoi_toa_tang']
NUM = ['so_phong']

def remove_accents(x):
    s = unicodedata.normalize('NFD', str(x).lower().strip()).replace('đ','d')
    return ''.join(c for c in s if not unicodedata.combining(c))

def normalize_buoi(value):
    return {'sang':'Sáng','chieu':'Chiều','toi':'Tối'}.get(remove_accents(value),'')

def features(df, advanced=False):
    x = df.copy()
    x['thu'] = x['thu'].astype(int).astype(str)
    x['tang'] = x['tang'].astype(int).astype(str)
    x['toa_tang'] = x['toa_nha'].astype(str) + '|' + x['tang']
    x['thu_buoi'] = x['thu'] + '|' + x['buoi'].astype(str)
    x['thu_buoi_toa_tang'] = x['thu_buoi'] + '|' + x['toa_tang']
    cats = CAT.copy()
    nums = NUM.copy()
    if advanced:
        x['thu_buoi_tiet'] = (x['thu_buoi'] + '|' +
            x['tiet_bat_dau'].astype(int).astype(str) + '-' +
            x['tiet_ket_thuc'].astype(int).astype(str))
        cats.append('thu_buoi_tiet')
        nums += ['tiet_bat_dau','tiet_ket_thuc']
    return x[cats + nums]

def history_scores(train, query, config, advanced=False):
    # Ma trận: (số truy vấn, số ca lịch sử). Không dùng tên môn.
    a = train.reset_index(drop=True)
    q = query.reset_index(drop=True)
    day = q.thu.to_numpy()[:,None] == a.thu.to_numpy()[None,:]
    session = q.buoi.to_numpy()[:,None] == a.buoi.to_numpy()[None,:]
    building = q.toa_nha.to_numpy()[:,None] == a.toa_nha.to_numpy()[None,:]
    physical = building & (q.toa_nha.to_numpy()[:,None] != 'ONLINE')
    floor = physical & (q.tang.to_numpy()[:,None] == a.tang.to_numpy()[None,:])
    room = physical & (q.phong.to_numpy()[:,None] == a.phong.to_numpy()[None,:])
    same_time = day & session
    c = config
    similarities = (c['day']*day + c['session']*session +
                    c['joint']*same_time + c['building']*physical +
                    c['floor']*floor + c['room']*room).astype(float)
    if advanced:
        start = np.maximum(q.tiet_bat_dau.to_numpy()[:,None],
                           a.tiet_bat_dau.to_numpy()[None,:])
        end = np.minimum(q.tiet_ket_thuc.to_numpy()[:,None],
                         a.tiet_ket_thuc.to_numpy()[None,:])
        overlap = np.maximum(0, end - start + 1)
        dur = np.maximum(1, q.tiet_ket_thuc.to_numpy() -
                         q.tiet_bat_dau.to_numpy() + 1)[:,None]
        similarities += c['period'] * same_time * overlap / dur
    # Thói quen gần đây: chỉ ưu tiên ca HK2 trong cùng tập Train.
    recency = np.where(a.hoc_ky.astype(str).to_numpy() == '2',
                       c['recent'], 1.0)
    similarities *= recency[None,:]
    teachers = np.array(sorted(a.giang_vien.unique()))
    score = np.empty((len(q), len(teachers)), dtype=float)
    support = np.zeros((len(q), len(teachers)), dtype=int)
    for j, teacher in enumerate(teachers):
        idx = np.flatnonzero(a.giang_vien.to_numpy() == teacher)
        v = similarities[:,idx]
        top = np.sort(v, axis=1)[:,-min(3,len(idx)):]
        score[:,j] = 0.82*top[:,-1] + 0.18*top.mean(axis=1)
        support[:,j] = same_time[:,idx].sum(axis=1)
    return teachers, score, support

def parse_room(room):
    x = re.sub(r'\s+','',str(room).upper().strip())
    if re.fullmatch(r'ONLINE[\dA-Z]*',x):
        return ('ONLINE','ONLINE',-1,-1)
    m = re.fullmatch(r'([A-Z]{1,3})[.-]?(\d{2,4})([A-Z]?)',x)
    if not m: raise ValueError('Phòng không hợp lệ, VD: G501 hoặc Online18')
    b, digits, suffix = m.groups()
    floor = int(digits[:-2] or '0')
    if not 0 <= floor <= 30: raise ValueError('Tầng không hợp lệ')
    return (b+digits+suffix,b,floor,int(digits[-2:]))

def single_query(thu, buoi, phong, tiet_bat_dau=None, tiet_ket_thuc=None):
    s = remove_accents(thu).replace('thu ','').replace('thứ ','')
    if s in ('cn','chu nhat'): d=8
    elif s.isdigit() and 2<=int(s)<=8: d=int(s)
    else: raise ValueError('Thứ phải là 2-8 hoặc Chủ nhật')
    session = normalize_buoi(buoi)
    if not session: raise ValueError('Buổi phải là Sáng/Chiều/Tối')
    room,building,floor,number = parse_room(phong)
    p1 = 0 if tiet_bat_dau is None else int(tiet_bat_dau)
    p2 = 0 if tiet_ket_thuc is None else int(tiet_ket_thuc)
    if (p1==0) != (p2==0): raise ValueError('Nhập cả hai tiết hoặc bỏ trống')
    if p1 and not (1<=p1<=p2<=20): raise ValueError('Tiết ngoài phạm vi 1..20')
    return pd.DataFrame([dict(thu=d,buoi=session,phong=room,toa_nha=building,
                             tang=floor,so_phong=number,tiet_bat_dau=p1,
                             tiet_ket_thuc=p2)])
