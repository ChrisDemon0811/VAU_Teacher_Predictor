# -*- coding: utf-8 -*-
"""VAU Teacher Predictor — Streamlit, HK2 2026–27."""
from __future__ import annotations
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0,str(ROOT))
import pandas as pd
import streamlit as st
from model.predictor import load_assets, predict

st.set_page_config(page_title='VAU Teacher Predictor · HK2 2026–2027',page_icon='🎓',layout='wide',initial_sidebar_state='collapsed')
st.markdown('''<style>
.block-container {max-width:1120px;padding-top:2rem;padding-bottom:3rem}
h1,h2,h3 {letter-spacing:-.025em}
.small-muted{color:#64748b;font-size:0.94rem;line-height:1.65}
.header-top{padding:22px 25px;border:1px solid #d8e5f7;background:linear-gradient(120deg,#f7fbff,#ffffff);border-radius:16px;margin-bottom:22px}
.stButton button[kind="primary"]{font-weight:650;border-radius:9px}
</style>''',unsafe_allow_html=True)

try:
    _,config,report,catalog=load_assets()
except Exception as exc:
    st.error('Không thể nạp dữ liệu mô hình. Hãy kiểm tra thư mục model/ có đủ CSV và JSON.')
    st.exception(exc);st.stop()

st.markdown('''<div class="header-top"><div style="font-size:13px;letter-spacing:1.1px;font-weight:750;color:#2563eb">HỌC VIỆN HÀNG KHÔNG VIỆT NAM · DEMO</div>
<h1 style="margin:10px 0 4px">🎓 VAU Teacher Predictor</h1><div class="small-muted">Gợi ý giảng viên cho <b>Học kỳ 2 · Năm học 2026–2027</b> dựa trên lịch sử thời khóa biểu, kể cả môn học cùng kỳ năm trước.</div></div>''',unsafe_allow_html=True)
st.info('Đây là dự đoán tham khảo, **không phải thông báo phân công giảng viên chính thức**. Điểm xếp hạng không phải xác suất.')

with st.sidebar:
    st.header('Giới thiệu mô hình')
    st.write('**Thuật toán:** Historical Matching kết hợp thông tin môn học từng được phân công giảng dạy.')
    st.caption('Đã sử dụng dữ liệu lịch sử đến HK1 2026–2027 (bản lưu có sẵn). Không có dữ liệu tương lai HK2 2026–2027.')
    st.metric('Số ca lịch sử Train cuối',f"{report['final_train_rows']:,}")
    st.metric('Số môn HK2 năm trước',f"{report['raw_hk2_subjects']}")
    val=report['validation']
    st.metric('Top 3 Validation trước Bước 10.1',f"{val['top3']*100:.2f}%".replace('.', ','))
    st.warning('41,86% là kết quả Validation trước khi bổ sung Bước 10.1, chưa phải điểm đánh giá mô hình mới. Chưa xác nhận độ chính xác trong HK2 2026–2027; tập Test trước đã được tham khảo nhiều lần.')
    st.markdown('[Thời khóa biểu chính thức của VAU](https://pdt.vau.edu.vn/tra-cuu-thoi-khoa-bieu)')

subjects=sorted(catalog['ten_mon'].dropna().astype(str).unique().tolist(),key=str.casefold)
left,right=st.columns([1.5,1],gap='large')
with left:
    st.subheader('Nhập thông tin học phần')
    st.caption('Bạn có thể nhập cả môn học để tận dụng dữ liệu HK2 2025–2026. Nếu môn chưa có trong lịch sử, hệ thống tự dự đoán bằng giờ/phòng.')
    with st.form('prediction_form',clear_on_submit=False):
        mon=st.selectbox('Môn học dự định đăng ký (không bắt buộc)', ['Chưa chọn môn']+subjects,help='Các môn lấy trực tiếp từ dữ liệu HK2 năm 2025–2026; không tự tạo danh sách.')
        other=st.text_input('Hoặc nhập tên môn khác',placeholder='Ví dụ: Học máy (nếu không thấy trong danh sách)')
        cc1,cc2=st.columns(2)
        with cc1:thu=st.selectbox('Thứ',list(range(2,9)),format_func=lambda x: 'Chủ nhật' if x==8 else f'Thứ {x}',index=3)
        with cc2:buoi=st.selectbox('Buổi học',['Sáng','Chiều','Tối'])
        phong=st.text_input('Phòng học',value='G502',help='Ví dụ: G502, K02, K04, K501, Online18. Phòng có thể chưa có lịch sử trong các kỳ trước.')
        include_period=st.checkbox('Tôi biết tiết bắt đầu và tiết kết thúc')
        if include_period:
            pc1,pc2=st.columns(2)
            with pc1:tiet_bat_dau=st.number_input('Tiết bắt đầu',1,20,1,1)
            with pc2:tiet_ket_thuc=st.number_input('Tiết kết thúc',1,20,5,1)
        else:tiet_bat_dau=tiet_ket_thuc=None
        submitted=st.form_submit_button('🔎 Dự đoán giảng viên',type='primary',use_container_width=True)
with right:
    st.subheader('Nguồn dữ liệu')
    st.markdown('**Dữ liệu lịch sử đã gộp**')
    for key,number in report['final_train_by_term'].items():
        st.write(f"- {key.replace('_HK',' · HK')}: **{number} ca**")
    st.caption('HK2 2025–2026 đã có 195 ca trực tiếp trong Train cũ. Có thêm 89 ca Online được kiểm tra, nhưng cách đưa chúng vào Train được chọn theo kết quả Validation.')
    st.markdown('**Về tòa K**')
    st.caption(f"Tòa K bắt đầu sử dụng từ HK1 năm 2026–2027. Lịch sử hiện có {report['final_train_buildings']['K']} ca tòa K, gồm {report['buoc10_1']['K_tret_sau']} ca tầng trệt; chưa được kiểm chứng riêng cho HK2 mới.")

if submitted:
    st.divider()
    chosen=other.strip() or (mon if mon!='Chưa chọn môn' else None)
    try:
        with st.spinner('Đang tính điểm tương đồng từ lịch sử...'):
            result=predict(thu,buoi,phong,tiet_bat_dau,tiet_ket_thuc,chosen,3)
    except (ValueError,TypeError) as exc:
        st.error(str(exc));st.stop()
    except Exception as exc:
        st.error('Không thể thực hiện dự đoán do dữ liệu hoặc cấu hình.');st.exception(exc);st.stop()
    st.subheader('Kết quả Top 3 giảng viên')
    st.caption(f"Dự đoán cho: {'Chủ nhật' if thu==8 else f'Thứ {thu}'} · {buoi} · {phong.upper().strip()}"+(f' · {chosen}' if chosen else ''))
    if chosen and result.get('co_su_dung_mon_hoc'):
        st.success('Có lịch sử giảng viên dạy môn này trong dữ liệu cũ; đã cộng tín hiệu môn học vào xếp hạng.')
    elif chosen:
        st.warning('Môn vừa nhập chưa có lịch sử phù hợp; kết quả chỉ dựa vào thời gian và địa điểm.')
    if result.get('toa_moi_chua_co_lich_su'):
        st.warning('Địa điểm mới, chưa có dữ liệu phòng/tầng: dự đoán theo thời gian và môn học nếu có.')
    if result.get('canh_bao_tang_tret'):
        st.warning(result['canh_bao_tang_tret'])
    for idx, item in enumerate(result.get('ket_qua',[]),1):
        with st.container(border=True):
            a,b=st.columns([4,1])
            with a:
                st.markdown(f'**#{idx} — {item["giang_vien"]}**')
                st.caption(f'Ca trùng thứ/buổi: {item["so_ca_lich_su_trung_thu_buoi"]} · Nhóm lớp đã từng dạy môn này: {item["so_nhom_lop_tung_day_mon"]}')
                signals=[f'🕒 **Thời gian:** {item["so_ca_lich_su_trung_thu_buoi"]} ca lịch sử trùng thứ và buổi.']
                if result.get('toa_moi_chua_co_lich_su'):
                    signals.append('📍 **Phòng học:** tòa chưa có trong Train; không dùng tín hiệu tòa, tầng hoặc phòng.')
                elif result.get('che_do')=='chi_thoi_gian_online':
                    signals.append('📍 **Phòng học:** lớp Online; không gán tòa hoặc tầng vật lý.')
                else:
                    signals.append(f'📍 **Phòng học:** {item["so_ca_trung_phong"]} ca cùng phòng, {item["so_ca_trung_tang"]} ca cùng tầng và {item["so_ca_trung_toa_nha"]} ca cùng tòa.')
                if chosen and item.get('da_tung_day_mon'):
                    signals.append(f'📚 **Môn học:** đã ghi nhận {item["so_nhom_lop_tung_day_mon"]} nhóm lớp của môn này.')
                elif chosen:
                    signals.append('📚 **Môn học:** chưa ghi nhận giảng viên này dạy môn đã chọn; không cộng điểm môn học.')
                else:
                    signals.append('📚 **Môn học:** người dùng không chọn, nên tín hiệu môn học không tham gia xếp hạng.')
                st.markdown('  \n'.join(signals))
            with b:
                st.metric('Điểm xếp hạng',f'{item["diem_xep_hang"]:.2f}')
    if result.get('so_giang_vien_dong_diem_cao_nhat',0)>3:
        st.warning(f"Có {result['so_giang_vien_dong_diem_cao_nhat']} giảng viên đồng điểm cao nhất. Top 3 không có cơ sở chắc chắn để phân biệt họ.")
        with st.expander('Xem tất cả giảng viên đồng điểm'):
            st.dataframe(pd.DataFrame(result['giang_vien_dong_diem_cao_nhat']),hide_index=True,use_container_width=True)
    st.caption(result.get('canh_bao',''))
else:
    st.divider()
    st.caption('Chọn môn học, nhập lịch và nhấn “Dự đoán giảng viên” để xem kết quả. Bạn không cần chọn môn nếu chưa biết môn sẽ đăng ký.')
