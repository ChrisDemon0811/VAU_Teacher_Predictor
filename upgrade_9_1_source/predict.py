import json
from pathlib import Path
import joblib
import pandas as pd
from prediction_engine import features, history_scores, single_query

ROOT=Path(__file__).resolve().parent
META=json.loads((ROOT/'model_metadata.json').read_text(encoding='utf-8'))

def predict(thu,buoi,phong,tiet_bat_dau=None,tiet_ket_thuc=None,top_k=3):
    q=single_query(thu,buoi,phong,tiet_bat_dau,tiet_ket_thuc)
    # Dùng model basic khi không có tiết, nếu không model advanced có thể được chọn.
    config = META['basic'] if tiet_bat_dau is None else META['advanced']
    advanced = tiet_bat_dau is not None
    if config['family']=='History':
        hist=pd.read_csv(ROOT/config['train_file'],encoding='utf-8-sig')
        names,scores,support=history_scores(hist,q,config['weights'],advanced)
        sc=scores[0]
        support=support[0]
    else:
        model=joblib.load(ROOT/config['file'])
        names=model.classes_
        sc=model.predict_proba(features(q,advanced))[0]
        support=None
    order=sc.argsort()[::-1][:max(1,min(int(top_k),len(names)))]
    gap=float(sc[order[0]]-sc[order[1]]) if len(order)>1 else 0.0
    threshold=config.get('validation_margin_threshold')
    confident=(threshold is not None and gap>=threshold)
    ranked=[]
    for i in order:
        rec=dict(giang_vien=str(names[i]),diem_xep_hang=float(sc[i]))
        if support is not None: rec['so_ca_lich_su_trung_thu_buoi']=int(support[i])
        ranked.append(rec)
    return dict(ket_qua=ranked,du_doan_co_co_so_kiem_dinh=bool(confident),
                thong_bao=('Có bằng chứng trên Validation cho ngưỡng chấp nhận.'
                           if confident else 'Độ tin cậy chưa được kiểm chứng đủ; chỉ tham khảo.'),
                canh_bao='Không phải tên giảng viên chính thức. Điểm xếp hạng không nhất thiết là xác suất.',
                model=config['name'])

if __name__=='__main__':
    print(json.dumps(predict(5,'Sáng','G502'),ensure_ascii=False,indent=2))
