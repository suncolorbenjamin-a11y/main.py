import data_engine
from datetime import datetime, timedelta

def add_subject(data, name, schedule, class_time):
    if name and name not in data["subjects"]:
        data["subjects"][name] = {"schedule": schedule, "class_time": class_time, "tasks": {}}
        data_engine.save_data(data)
        return True
    return False

def update_subject(data, name, schedule, class_time):
    """【新功能】僅修改設定，不影響任務內容"""
    if name in data["subjects"]:
        data["subjects"][name]["schedule"] = schedule
        data["subjects"][name]["class_time"] = class_time
        data_engine.save_data(data)
        return True
    return False

def delete_subject(data, name):
    if name in data["subjects"]:
        del data["subjects"][name]
        data_engine.save_data(data)
        return True
    return False

def add_or_update_task(data, subject_name, task_name, total, weight, t_type):
    if subject_name in data["subjects"]:
        current = data["subjects"][subject_name]["tasks"].get(task_name, {"done": 0})
        done = current.get("done", 0) if isinstance(current, dict) else current[0]
        data["subjects"][subject_name]["tasks"][task_name] = {
            "done": done, "total": total, "weight": weight, "type": t_type
        }
        data_engine.save_data(data)
        return True
    return False

def delete_task(data, subject_name, task_name):
    if subject_name in data["subjects"] and task_name in data["subjects"][subject_name]["tasks"]:
        del data["subjects"][subject_name]["tasks"][task_name]
        data_engine.save_data(data)
        return True
    return False

def add_subject(data, name, schedule, class_time):
    """新增科目，包含上課時間 (格式如 "09:00")"""
    if name and name not in data["subjects"]:
        data["subjects"][name] = {
            "schedule": schedule, 
            "class_time": str(class_time), # 存成字串 "HH:MM"
            "tasks": {}
        }
        data_engine.save_data(data)
        return True
    return False

def auto_reset_subjects(data):
    """檢查每一科是否該自動結算"""
    now = datetime.now()
    today_idx = now.weekday()
    updated = False

    for name, info in data["subjects"].items():
        # 1. 取得這科設定的時間
        time_str = info.get("class_time", "09:00")
        t_h, t_m = map(int, time_str.split(":"))
        
        # 2. 找出「最近一次」應該上課的時間點 (這週的上課日)
        # 這裡簡化邏輯：如果今天就是上課日且時間已過，或是上課日已過，就該結算
        last_reset_str = info.get("last_reset_date", "1970-01-01")
        last_reset = datetime.strptime(last_reset_str, "%Y-%m-%d").date()
        
        for class_day in info["schedule"]:
            # 計算這週該上課日的日期
            days_diff = today_idx - class_day
            this_week_class_date = (now - timedelta(days=days_diff)).date()
            this_week_class_dt = datetime.combine(this_week_class_date, datetime.strptime(time_str, "%H:%M").time())
            
            # 如果：這週上課時間已過 + 且這週還沒結算過 (last_reset 在上課日之前)
            if now > this_week_class_dt and last_reset < this_week_class_date:
                # --- 執行結算 ---
                # 計算該科總產出
                sub_total = sum(t.get("done", 0) if isinstance(t, dict) else t[0] 
                               for t in info["tasks"].values())
                
                # 存入歷史
                data["history"].append({
    "date": str(this_week_class_date),
    "subject": name,
    "solved": 0,      # 👈 改為 0！因為產出已經被按鈕即時紀錄了
    "total": sub_total # 👈 保留這個，用來算達成率的母數
})
                
                # 進度歸零
                for t_name in info["tasks"]:
                    if isinstance(info["tasks"][t_name], dict):
                        info["tasks"][t_name]["done"] = 0
                    else:
                        info["tasks"][t_name][0] = 0
                
                # 更新這科的最後結算日
                info["last_reset_date"] = str(this_week_class_date)
                updated = True
    
    if updated:
        data_engine.save_data(data)
    return updated