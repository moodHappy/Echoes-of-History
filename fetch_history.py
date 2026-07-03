import os
import requests
import json
import random
import re
from datetime import datetime, timezone, timedelta

# ================= 配置区 =================
BASE_DIR = "docs"
tz_utc_8 = timezone(timedelta(hours=8))

# 灵感偏好权重关键字
PREFERENCE_KEYWORDS = ["roman", "ottoman", "byzantine", "china", "emperor", "sultan", "dynasty", "king", "war", "treaty"]

# 创意写作灵感触发器模板
PROMPT_TEMPLATES = [
    "⚔️ 世界观种子：如果事件中的核心矛盾发生在一个魔幻/蒸汽朋克世界，历史会如何脱轨？",
    "🎭 角色切入点：塑造一个身处这场历史漩涡最底层的普通人，他/她将如何做出一项艰难的抉择？",
    "🔮 历史暗流：假设这场事件背后其实有一个隐秘的组织在操纵，他们的终极目的是什么？",
    "📜 编年史裂痕：如果某个关键人物在事件发生的五分钟前改变了主意，后世的版图会发生什么巨变？",
    "🏰 空间构建：以此事件发生的核心场所为原型，描绘一个充满了悬疑与权力斗争的封闭舞台。"
]
# ==========================================

def fetch_wikipedia_history(month, day):
    print(f"📜 正在开启时间长河的信道，正在检索 {month}月{day}日 的历史星图...")
    m_str = f"{month:02d}"
    d_str = f"{day:02d}"
    url = f"https://en.wikipedia.org/api/rest_v1/feed/onthisday/all/{m_str}/{d_str}"

    headers = {'User-Agent': 'EchoesOfHistoryBot/1.0 (Contact: admin@nexus.hub)'}
    try:
        res = requests.get(url, headers=headers, timeout=15)
        if res.status_code == 200:
            return res.json()
    except Exception as e:
        print(f"❌ 时间信道连接失败: {e}")
    return None

def extract_blind_box_events(data):
    if not data or 'selected' not in data:
        return []

    raw_events = data['selected']
    scored_events = []

    for ev in raw_events:
        text = ev.get('text', '')
        year = ev.get('year', 0)
        pages = ev.get('pages', [])

        wiki_links = []
        for p in pages:
            if 'titles' in p and 'normalized' in p['titles']:
                wiki_links.append({
                    "title": p['titles']['normalized'],
                    "url": p.get('content_urls', {}).get('desktop', {}).get('page', '')
                })

        score = 0
        text_lower = text.lower()
        for kw in PREFERENCE_KEYWORDS:
            if kw in text_lower:
                score += 10

        score += random.randint(1, 5)

        scored_events.append({
            "year": year,
            "text": text,
            "links": wiki_links,
            "score": score
        })

    scored_events.sort(key=lambda x: x['score'], reverse=True)
    return scored_events[:5]

def save_daily_blind_box(events, now_obj):
    year_str, month_str = str(now_obj.year), str(now_obj.month)
    target_dir = os.path.join(BASE_DIR, year_str, month_str)
    os.makedirs(target_dir, exist_ok=True)

    filename = f"{now_obj.year}_{now_obj.month}_{now_obj.day}_{now_obj.strftime('%H%M')}.html"
    html_path = os.path.join(target_dir, filename)

    events_html = ""
    for idx, ev in enumerate(events):
        inspiration_prompt = random.choice(PROMPT_TEMPLATES)
        links_html = ""
        if ev['links']:
            links_html = '<div class="wiki-refs"><b>References:</b> ' + " | ".join([f'<a href="{l["url"]}" target="_blank">{l["title"]}</a>' for l in ev['links']]) + '</div>'

        events_html += f"""
        <div class="archive-card">
            <div class="card-epoch">📍 ANNO DOMINI {ev['year']}</div>
            <div class="card-text">{ev['text']}</div>
            {links_html}
            <div class="inspiration-box">
                <div class="prompt-title">📝 灵感回响 (Inspiration Spark)</div>
                <div class="prompt-body">{inspiration_prompt}</div>
            </div>
        </div>
        """

    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>Echoes of History - Blind Box</title>
    <style>
        :root {{ 
            --parchment-bg: #fcf8f2; 
            --parchment-border: #e8dfd1; 
            --ink-dark: #2c2421; 
            --ink-muted: #70625a; 
            --imperial-blue: #1a365d; 
            --accent-crimson: #8c1d40; 
        }}
        body {{ 
            background: var(--parchment-bg); 
            color: var(--ink-dark); 
            font-family: "Georgia", Garamond, serif; 
            margin: 0; padding: 0; 
            -webkit-font-smoothing: antialiased; 
            line-height: 1.6;
        }}
        .nav-header {{
            background: rgba(252, 248, 242, 0.9);
            backdrop-filter: blur(10px);
            border-bottom: 1px solid var(--parchment-border);
            padding: 15px 20px;
            position: sticky; top: 0; z-index: 100;
            display: flex; justify-content: space-between; align-items: center;
        }}
        .nav-header a {{
            color: var(--imperial-blue);
            text-decoration: none;
            font-weight: bold;
            font-size: 0.95rem;
            font-family: -apple-system, BlinkMacSystemFont, sans-serif;
        }}
        .container {{ max-width: 650px; margin: 0 auto; padding: 30px 15px 60px 15px; }}
        
        .box-title {{ text-align: center; margin-bottom: 40px; border-bottom: 2px double var(--parchment-border); padding-bottom: 20px; }}
        .box-title h1 {{ font-size: 2.2rem; font-weight: normal; margin: 0 0 10px 0; color: var(--accent-crimson); font-style: italic; }}
        .box-title p {{ margin: 0; color: var(--ink-muted); font-size: 0.95rem; letter-spacing: 1px; text-transform: uppercase; }}
        
        .archive-card {{
            background: #ffffff;
            border: 1px solid var(--parchment-border);
            border-radius: 12px;
            padding: 25px;
            margin-bottom: 30px;
            box-shadow: 0 4px 20px rgba(44,36,33,0.03);
            position: relative;
        }}
        .card-epoch {{
            font-size: 0.85rem;
            font-weight: bold;
            color: var(--accent-crimson);
            letter-spacing: 1.5px;
            margin-bottom: 12px;
            font-family: -apple-system, BlinkMacSystemFont, sans-serif;
        }}
        .card-text {{
            font-size: 1.15rem;
            color: var(--ink-dark);
            margin-bottom: 15px;
            text-align: justify;
        }}
        .wiki-refs {{
            font-size: 0.85rem;
            color: var(--ink-muted);
            border-top: 1px dashed var(--parchment-border);
            padding-top: 12px;
            margin-bottom: 15px;
            font-family: -apple-system, BlinkMacSystemFont, sans-serif;
            white-space: nowrap; overflow-x: auto; scrollbar-width: none;
        }}
        .wiki-refs::-webkit-scrollbar {{ display: none; }}
        .wiki-refs a {{ color: var(--imperial-blue); text-decoration: none; font-weight: 500; margin: 0 2px; }}
        .wiki-refs a:hover {{ text-decoration: underline; }}
        
        .inspiration-box {{
            background: #fdfbf7;
            border-left: 3px solid var(--imperial-blue);
            padding: 12px 16px;
            border-radius: 0 8px 8px 0;
        }}
        .prompt-title {{
            font-size: 0.85rem;
            font-weight: 700;
            color: var(--imperial-blue);
            margin-bottom: 6px;
            font-family: -apple-system, BlinkMacSystemFont, sans-serif;
        }}
        .prompt-body {{ font-size: 0.95rem; color: var(--ink-dark); font-style: italic; }}
    </style>
</head>
<body>
    <div class="nav-header">
        <a href="../../index.html">📜 Return to Chronicle</a>
        <span style="font-size:0.9rem; color:var(--ink-muted); font-family:sans-serif;">{now_obj.strftime('%Y-%m-%d')}</span>
    </div>
    <div class="container">
        <div class="box-title">
            <h1>Echoes of History</h1>
            <p>~ 今日份虚空历史盲盒 ~</p>
        </div>
        {events_html}
    </div>
</body>
</html>"""

    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html_content)
    print(f"🎉 盲盒卷宗已封印入库: {html_path}")
    return f"{year_str}/{month_str}/{filename}"

def generate_chronicle_hub():
    archive_data = {}
    if os.path.exists(BASE_DIR):
        years = [d for d in os.listdir(BASE_DIR) if d.isdigit()]
        for year in years:
            archive_data[year] = {}
            months = [d for d in os.listdir(os.path.join(BASE_DIR, year)) if d.isdigit()]
            for month in months:
                archive_data[year][month] = {}
                files = sorted([f for f in os.listdir(os.path.join(BASE_DIR, year, month)) if f.endswith('.html')], reverse=True)
                for file in files:
                    try:
                        parts = file.replace(".html", "").split('_')
                        if len(parts) == 4:
                            day = parts[2]
                            time_str = f"{parts[3][:2]}:{parts[3][2:]}"
                            file_path = f"{year}/{month}/{file}"

                            if day not in archive_data[year][month]:
                                archive_data[year][month][day] = []

                            archive_data[year][month][day].append({
                                "time": time_str,
                                "path": file_path,
                                "title": "单集精读: 历史盲盒已送达"
                            })
                    except: pass

    json_data = json.dumps(archive_data)

    html_template = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>Echoes of History - 历史档案馆</title>
    <style>
        :root { 
            --parchment-bg: #f4f5f7; /* 更贴近图片的浅灰背景 */
            --parchment-border: #e6dfd3; 
            --ink-dark: #cc0000; /* 图片中文字偏红 */
            --ink-muted: #7c7066; 
            --imperial: #ff3b30; 
            --card-bg: #ffffff;
        }
        body, html { 
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; 
            -webkit-font-smoothing: antialiased; 
            background: var(--parchment-bg); 
            margin: 0; padding: 0; color: var(--ink-dark); 
            height: 100%;
        }
        .app-layout { display: flex; flex-direction: column; height: 100%; }
        .header-panel { text-align: center; padding: 25px 20px 15px 20px; border-bottom: 1px dashed var(--parchment-border); }
        .header-panel h1 { font-size: 2.0rem; font-weight: normal; margin: 0 0 8px 0; font-style: italic; color: #8c1d40; font-family: Georgia, serif; }
        
        .main-content { flex: 1; overflow-y: auto; padding: 15px; }
        .container { max-width: 600px; margin: 0 auto; }
        
        /* 日历控制条 */
        .cal-controls { display: flex; justify-content: center; align-items: center; gap: 12px; margin-bottom: 15px; }
        .cal-btn { background: #8c1d40; color: #fff; border: none; border-radius: 6px; padding: 8px 14px; font-size: 14px; cursor: pointer; font-weight: bold; }
        .select-shell { padding: 6px 12px; border: 1px solid var(--parchment-border); border-radius: 6px; font-size: 15px; background: #fff; font-weight: bold; outline: none; }
        
        /* 羊皮纸日历架构 */
        .calendar-box { 
            background: var(--card-bg); border-radius: 16px; 
            padding: 15px; box-shadow: 0 2px 10px rgba(0,0,0,0.03); margin-bottom: 20px; 
            user-select: none; -webkit-user-select: none; transition: border 0.3s, box-shadow 0.3s;
            border: 2px solid transparent;
        }
        .calendar-box.edit-mode-active { border: 2px dashed #ff3b30; }
        
        .weekdays { display: grid; grid-template-columns: repeat(7, 1fr); text-align: center; font-weight: bold; font-size: 13px; color: #a0a0a0; margin-bottom: 10px; padding-bottom: 5px; }
        .days-grid { display: grid; grid-template-columns: repeat(7, 1fr); gap: 6px; }
        .day-cell { aspect-ratio: 1; display: flex; flex-direction: column; justify-content: center; align-items: center; font-size: 16px; font-weight: 500; border-radius: 10px; cursor: pointer; position: relative; transition: all 0.2s; }
        .day-cell.empty { visibility: hidden; }
        .day-cell.has-news { color: #333; }
        .day-cell.no-news { color: #ccc; }
        .day-cell.selected { background: #ffebee; border: 1px solid #ff3b30; color: #ff3b30; }
        .day-cell.today { background: #f0f0f0; }
        .dot { width: 4px; height: 4px; background-color: #ff3b30; border-radius: 50%; position: absolute; bottom: 8px; display: none; }
        .day-cell.has-news .dot { display: block; }
        
        /* 盲盒抽取结果列表 (精确复刻图片UI) */
        .feed-list { display: flex; flex-direction: column; gap: 12px; }
        .feed-item-wrapper { 
            display: flex; gap: 10px; align-items: stretch; width: 100%; 
        }
        .feed-item { 
            flex: 1; 
            background: var(--card-bg); 
            border-radius: 12px; 
            padding: 18px 16px; 
            display: flex; 
            align-items: center; 
            text-decoration: none; 
            color: #d32f2f; 
            font-weight: 500;
            font-size: 15px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.03); 
            /* 左侧红色高亮边框 */
            border-left: 5px solid #ff3b30; 
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }
        .feed-item:active { background: #f9f9f9; }
        .feed-title { margin-left: 5px; overflow: hidden; text-overflow: ellipsis; }
        .empty-placeholder { text-align: center; padding: 40px 20px; color: #a0a0a0; font-size: 14px; }
        
        /* 删除按钮系统 */
        .del-btn { 
            background: #ff443a; 
            color: #fff; 
            border: none; 
            border-radius: 14px; 
            width: 58px; 
            flex-shrink: 0;
            display: flex;
            justify-content: center;
            align-items: center;
            font-size: 22px; 
            cursor: pointer; 
            display: none; /* 默认隐藏 */
            transition: transform 0.1s;
        }
        .del-btn:active { transform: scale(0.92); }
        .edit-mode .del-btn { display: flex; }
    </style>
</head>
<body>
    <div class="app-layout">
        <div class="header-panel">
            <h1>Echoes of History</h1>
        </div>
        
        <div class="main-content">
            <div class="container">
                <div class="cal-controls">
                    <button class="cal-btn" id="prevBtn">&lt;</button>
                    <select class="select-shell" id="yearSelect"></select>
                    <select class="select-shell" id="monthSelect">
                        <option value="1">01月</option><option value="2">02月</option><option value="3">03月</option>
                        <option value="4">04月</option><option value="5">05月</option><option value="6">06月</option>
                        <option value="7">07月</option><option value="8">08月</option><option value="9">09月</option>
                        <option value="10">10月</option><option value="11">11月</option><option value="12">12月</option>
                    </select>
                    <button class="cal-btn" id="nextBtn">&gt;</button>
                    <button class="cal-btn" id="todayBtn">今日</button>
                </div>

                <!-- 长按或双击此区域切换编辑模式 -->
                <div class="calendar-box" id="calendarBox">
                    <div class="weekdays"><span>22</span><span>23</span><span>24</span><span>25</span><span>26</span><span>27</span><span>28</span></div>
                    <div class="days-grid" id="daysGrid"></div>
                </div>

                <div class="feed-list" id="feedList"></div>
            </div>
        </div>
    </div>

    <script>
        const archiveData = {REPLACEME_JSON_DATA};
        const today = new Date();
        let selectedYear = today.getFullYear();
        let selectedMonth = today.getMonth() + 1;
        let selectedDay = today.getDate();

        const yearSelect = document.getElementById('yearSelect');
        const monthSelect = document.getElementById('monthSelect');
        const daysGrid = document.getElementById('daysGrid');
        const feedList = document.getElementById('feedList');
        const calendarBox = document.getElementById('calendarBox');

        // ================= 触发编辑模式 =================
        function toggleEditMode() {
            feedList.classList.toggle('edit-mode');
            calendarBox.classList.toggle('edit-mode-active');
        }

        // 1. 移动端长按支持 (600ms)
        let pressTimer;
        calendarBox.addEventListener('touchstart', (e) => {
            pressTimer = setTimeout(toggleEditMode, 600);
        }, {passive: true});
        calendarBox.addEventListener('touchend', () => clearTimeout(pressTimer));
        calendarBox.addEventListener('touchmove', () => clearTimeout(pressTimer));
        
        // 2. PC端双击保留
        calendarBox.addEventListener('dblclick', toggleEditMode);
        // ===============================================

        function initDropdowns() {
            const years = Object.keys(archiveData).map(Number).sort((a, b) => b - a);
            if (!years.includes(selectedYear)) years.unshift(selectedYear);
            years.forEach(y => {
                const opt = document.createElement('option'); opt.value = y; opt.textContent = y + ' 年';
                yearSelect.appendChild(opt);
            });
            yearSelect.value = selectedYear; monthSelect.value = selectedMonth;
        }

        function renderCalendarGrid(year, month) {
            daysGrid.innerHTML = '';
            const firstDay = new Date(year, month - 1, 1).getDay();
            const startDay = firstDay === 0 ? 7 : firstDay;
            const daysInMonth = new Date(year, month, 0).getDate();
            
            for (let i = 1; i < startDay; i++) {
                const empty = document.createElement('div'); empty.className = 'day-cell empty';
                daysGrid.appendChild(empty);
            }
            
            const monthData = (archiveData[year] && archiveData[year][month]) ? archiveData[year][month] : {};
            
            for (let day = 1; day <= daysInMonth; day++) {
                const cell = document.createElement('div'); cell.className = 'day-cell'; cell.textContent = day;
                const dot = document.createElement('div'); dot.className = 'dot'; cell.appendChild(dot);
                
                if (monthData[day] && monthData[day].length > 0) cell.classList.add('has-news'); else cell.classList.add('no-news');
                if (year === today.getFullYear() && month === today.getMonth() + 1 && day === today.getDate()) cell.classList.add('today');
                if (year === selectedYear && month === selectedMonth && day === selectedDay) cell.classList.add('selected');
                
                cell.addEventListener('click', () => {
                    selectedYear = year; selectedMonth = month; selectedDay = day;
                    renderCalendarGrid(year, month); renderBoxList(year, month, day);
                });
                daysGrid.appendChild(cell);
            }
        }

        function renderBoxList(year, month, day) {
            feedList.innerHTML = '';
            const monthData = (archiveData[year] && archiveData[year][month]) ? archiveData[year][month] : null;
            const dayData = monthData ? monthData[day] : null;
            
            if (dayData && dayData.length > 0) {
                dayData.forEach(item => {
                    const wrapper = document.createElement('div');
                    wrapper.className = 'feed-item-wrapper';
                    
                    const a = document.createElement('a'); a.href = item.path; a.className = 'feed-item';
                    a.innerHTML = `📌 <span class="feed-title">${item.title}</span>`;
                    
                    const delBtn = document.createElement('button');
                    delBtn.className = 'del-btn';
                    delBtn.innerHTML = '🗑️';
                    delBtn.onclick = (e) => {
                        e.preventDefault();
                        deleteToGitHub(item.path, wrapper, year, month, day);
                    };
                    
                    wrapper.appendChild(a);
                    wrapper.appendChild(delBtn);
                    feedList.appendChild(wrapper);
                });
            } else {
                feedList.innerHTML = '<div class="empty-placeholder">今日暂无案卷</div>';
            }
        }

        async function deleteToGitHub(path, elementToRemove, year, month, day) {
            if (!confirm(`确定要永久删除该记录并同步至 GitHub 吗？`)) return;
            
            let repo = localStorage.getItem('eh_gh_repo');
            let token = localStorage.getItem('eh_gh_token');
            
            if (!repo) {
                repo = prompt("请输入 GitHub 仓库名 (格式: owner/repo):");
                if (!repo) return;
                localStorage.setItem('eh_gh_repo', repo);
            }
            if (!token) {
                token = prompt("请输入具备该仓库操作权限的 GitHub Token (PAT):");
                if (!token) return;
                localStorage.setItem('eh_gh_token', token);
            }
            
            const apiUrl = `https://api.github.com/repos/${repo}/contents/docs/${path}`;
            
            try {
                const getRes = await fetch(apiUrl, { headers: { 'Authorization': `token ${token}` } });
                
                if (getRes.status === 404) {
                    removeLocalItem(year, month, day, path, elementToRemove);
                    return;
                }
                if (getRes.status === 401) {
                    alert("Token 无效或已过期，请点击重新尝试以配置。");
                    localStorage.removeItem('eh_gh_token');
                    return;
                }
                if (!getRes.ok) throw new Error("获取文件状态失败");
                
                const fileData = await getRes.json();
                
                const delRes = await fetch(apiUrl, {
                    method: 'DELETE',
                    headers: { 
                        'Authorization': `token ${token}`,
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        message: `Archive: Delete ${path} (via Web UI)`,
                        sha: fileData.sha
                    })
                });
                
                if (!delRes.ok) throw new Error("删除请求被远端拒绝");
                
                // 去除冗余通知，仅静默移除元素即可完成交互闭环
                removeLocalItem(year, month, day, path, elementToRemove);
                
            } catch (error) {
                console.error(error);
            }
        }

        function removeLocalItem(year, month, day, path, elementToRemove) {
            elementToRemove.remove(); 
            if (archiveData[year] && archiveData[year][month] && archiveData[year][month][day]) {
                archiveData[year][month][day] = archiveData[year][month][day].filter(i => i.path !== path);
                if (archiveData[year][month][day].length === 0) {
                    renderCalendarGrid(year, month);
                    feedList.innerHTML = '<div class="empty-placeholder">今日暂无案卷</div>';
                }
            }
        }

        yearSelect.addEventListener('change', (e) => { selectedYear = parseInt(e.target.value); renderCalendarGrid(selectedYear, selectedMonth); });
        monthSelect.addEventListener('change', (e) => { selectedMonth = parseInt(e.target.value); renderCalendarGrid(selectedYear, selectedMonth); });
        document.getElementById('prevBtn').addEventListener('click', () => { selectedMonth--; if (selectedMonth < 1) { selectedMonth = 12; selectedYear--; yearSelect.value = selectedYear; } monthSelect.value = selectedMonth; renderCalendarGrid(selectedYear, selectedMonth); });
        document.getElementById('nextBtn').addEventListener('click', () => { selectedMonth++; if (selectedMonth > 12) { selectedMonth = 1; selectedYear++; yearSelect.value = selectedYear; } monthSelect.value = selectedMonth; renderCalendarGrid(selectedYear, selectedMonth); });
        document.getElementById('todayBtn').addEventListener('click', () => { selectedYear = today.getFullYear(); selectedMonth = today.getMonth() + 1; selectedDay = today.getDate(); yearSelect.value = selectedYear; monthSelect.value = selectedMonth; renderCalendarGrid(selectedYear, selectedMonth); renderBoxList(selectedYear, selectedMonth, selectedDay); });

        initDropdowns(); renderCalendarGrid(selectedYear, selectedMonth); renderBoxList(selectedYear, selectedMonth, selectedDay);
    </script>
</body>
</html>"""

    final_html = html_template.replace("{REPLACEME_JSON_DATA}", json_data)
    with open(os.path.join(BASE_DIR, "index.html"), "w", encoding="utf-8") as f:
        f.write(final_html)
    print("🚀 主轴编年史大厅 index.html 编译同步完成！")

if __name__ == "__main__":
    os.makedirs(BASE_DIR, exist_ok=True)
    now = datetime.now(tz_utc_8)

    data = fetch_wikipedia_history(now.month, now.day)
    if data:
        best_events = extract_blind_box_events(data)
        if best_events:
            save_daily_blind_box(best_events, now)

    generate_chronicle_hub()

