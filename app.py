import streamlit as st
import json
import os

# --- 環境安全檢查（修正版） ---
def ensure_gcp_key():
    # 1. 如果本地已經有檔案了，就直接過關
    if os.path.exists("google_key.json"):
        return True
    
    # 2. 如果沒檔案，才去嘗試找雲端 Secrets
    try:
        # 使用 getattr 來避開 Streamlit 的直接報錯偵測
        secrets = getattr(st, "secrets", {})
        if "gcp_service_account" in secrets:
            with open("google_key.json", "w") as f:
                json.dump(dict(secrets["gcp_service_account"]), f)
            return True
    except:
        pass
    
    # 3. 兩邊都沒有，才顯示錯誤
    st.error("⚠️ 找不到 google_key.json，請確認檔案已放入專案資料夾中！")
    return False

# 執行檢查
if not ensure_gcp_key():
    st.stop() # 沒金鑰就先停住，避免後面報錯
# ---------------------------

from datetime import datetime
import data_engine, logic_engine, config_manager

st.set_page_config(page_title="🛡️ 考研戰情室", layout="wide")


if 'db' not in st.session_state:
    st.session_state.db = data_engine.load_data()
db = st.session_state.db

# --- 【新增】自動結算檢查 ---
# 每次重新整理網頁都會檢查是否有科目「剛上完課」
if config_manager.auto_reset_subjects(db):
    st.toast("⚡ 偵測到課程已結束，已自動結算並重置進度！")
    st.rerun()

# --- 側邊欄 ---
with st.sidebar:
    st.header("⚙️ 系統設定")
    
    with st.expander("➕ 科目管理"):
        # 讓用戶選擇是要「新增」還是「編輯現有科目」
        subject_options = ["科目修改"] + list(db["subjects"].keys())
        selected_sub = st.selectbox("選擇管理對象", subject_options)
        
        st.divider()
        
        if selected_sub == "科目修改":
            sub_n = st.text_input("新科目名稱")
            days = st.multiselect("上課日", ["週一", "週二", "週三", "週四", "週五", "週六", "週日"])
            c_time = st.time_input("上課時間點", value=datetime.strptime("09:00", "%H:%M").time())
            if st.button("確認新增科目", use_container_width=True):
                day_map = {"週一":0, "週二":1, "週三":2, "週四":3, "週五":4, "週六":5, "週日":6}
                if sub_n and days:
                    config_manager.add_subject(db, sub_n, [day_map[d] for d in days], c_time.strftime("%H:%M"))
                    st.rerun()
        else:
            # 編輯模式：自動帶入現有設定
            current_info = db["subjects"][selected_sub]
            day_map_rev = {0:"週一", 1:"週二", 2:"週三", 3:"週四", 4:"週五", 5:"週六", 6:"週日"}
            
            # 預設選中原本的日期
            default_days = [day_map_rev[d] for d in current_info["schedule"]]
            new_days = st.multiselect("修改上課日", ["週一", "週二", "週三", "週四", "週五", "週六", "週日"], default=default_days)
            
            # 預設顯示原本的時間
            curr_time_obj = datetime.strptime(current_info.get("class_time", "09:00"), "%H:%M").time()
            new_time = st.time_input("修改上課時間", value=curr_time_obj)
            
            if st.button("💾 更新科目設定", use_container_width=True):
                day_map = {"週一":0, "週二":1, "週三":2, "週四":3, "週五":4, "週六":5, "週日":6}
                config_manager.update_subject(db, selected_sub, [day_map[d] for d in new_days], new_time.strftime("%H:%M"))
                st.success(f"{selected_sub} 設定已更新！")
                st.rerun()
            
            if st.button("🗑️ 刪除整個科目", type="primary", use_container_width=True):
                config_manager.delete_subject(db, selected_sub)
                st.rerun()

    with st.expander("📝 任務設定/修改"):
        if db["subjects"]:
            sub_t = st.selectbox("選擇科目", list(db["subjects"].keys()), key="sub_t")
            t_name = st.text_input("任務名稱")
            t_type = st.radio("任務性質", ["實戰演練", "知識內化"], horizontal=True)
            if t_type == "實戰演練":
                t_total = st.number_input("目標題數", min_value=1, value=20, step=1)
            else:
                t_total = st.number_input("目標小時 (hr)", min_value=0.5, value=2.0, step=0.5)
            t_weight = st.slider("重要權重", 1, 5, 3)
            if st.button("儲存任務"):
                config_manager.add_or_update_task(db, sub_t, t_name, t_total, t_weight, t_type)
                st.rerun()
            st.divider()
            if db["subjects"][sub_t]["tasks"]:
                del_t = st.selectbox("刪除特定任務", list(db["subjects"][sub_t]["tasks"].keys()))
                if st.button("刪除任務"):
                    config_manager.delete_task(db, sub_t, del_t); st.rerun()
        else:
            st.write("請先新增科目")

    st.divider()

# --- 主畫面 ---
st.title("🛡️ 學業戰情總表")

stats = logic_engine.get_total_stats_by_type(db["subjects"])
c1, c2 = st.columns(2)
c1.metric("⚔️ 實戰演練總量", f"{int(stats['實戰演練'])} 題")
c2.metric("🧠 知識內化總量", f"{stats['知識內化']:.1f} hr")
st.write("---")

urg_list = logic_engine.get_urgency_report(db["subjects"])
for item in urg_list:
    with st.container():
        # 1. 擴展為四列：[科目資訊, 進度條, 百分比, 更新按鈕]
        # 比例調整為 2.5 : 3.5 : 1 : 1.5 確保文字不會太擠
        col1, col2, col_perc, col3 = st.columns([2.5, 3.5, 1, 1.5])
        
        # 第一列：燈號、名稱與倒數
        col1.subheader(f"{item['status']} {item['name']}")
        col1.caption(f"🕒 剩餘約 {item['hours_left']} 小時")
        
        # 第二列：進度條
        col2.write("") # 增加一個空行讓進度條稍微往下移，對齊文字中心
        col2.progress(item['progress'] / 100)
        
        # 第三列【新加入】：顯示進度 %
        col_perc.write("") # 同樣增加空行對齊
        col_perc.markdown(f"**{item['progress']:.1f}%**")
        
        # 第四列：按鈕
        if col3.button("更新進度", key=f"btn_{item['name']}", use_container_width=True):
            st.session_state.edit_target = None if st.session_state.get('edit_target') == item['name'] else item['name']
            st.rerun()

        if st.session_state.get('edit_target') == item['name']:
            st.info(f"正在更新 {item['name']}...")
            tasks = db["subjects"][item['name']].get("tasks", {})
            for tn, tv in tasks.items():
                c_txt, c_min, c_add = st.columns([2, 1, 1])
                is_dict = isinstance(tv, dict)
                t_type = tv.get("type", "知識內化") if is_dict else "知識內化"
                unit = "題" if t_type == "實戰演練" else "hr"
                step = 1 if t_type == "實戰演練" else 0.5
                done = tv.get("done", 0.0) if is_dict else tv[0]
                total = tv.get("total", 1.0) if is_dict else tv[1]
                
                c_txt.write(f"**{tn}** ({done}/{total} {unit})")
                if c_min.button(f"➖{step}", key=f"m_{tn}"):
                    db["subjects"][item['name']]["tasks"][tn]["done"] = max(0.0, done - step)
                    data_engine.log_activity(db, item['name'], -step)
                    data_engine.save_data(db); st.rerun()
                if c_add.button(f"➕{step}", key=f"a_{tn}"):
                    db["subjects"][item['name']]["tasks"][tn]["done"] = min(total, done + step)
                    data_engine.log_activity(db, item['name'], step)
                    data_engine.save_data(db); st.rerun()
    st.divider()

import analytics_engine
analytics_engine.show_analytics_dashboard(db["history"])