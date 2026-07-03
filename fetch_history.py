
import os
import requests
import json
import random
import re
from datetime import datetime, timezone, timedelta

# ================= 配置区 =================
BASE_DIR = "docs"
tz_utc_8 = timezone(timedelta(hours=8))

# 灵感偏好权重关键字（悄悄提升特定历史时期的爆出概率）
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
    """利用英文维基百科开放 API 获取指定日期的历史事件数据"""
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
    """从海量历史中提炼并筛选出最具有戏剧冲突和灵感价值的 5 个“盲盒”事件"""
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

        # 智能权重打分机制：文本包含特定历史偏好词时获得更高权重
        score = 0
        text_lower = text.lower()
        for kw in PREFERENCE_KEYWORDS:
            if kw in text_lower:
                score += 10

        # 加上随机微扰，确保每天的盲盒极具随机新鲜感
        score += random.randint(1, 5)

        scored_events.append({
            "year": year,
            "text": text,
            "links": wiki_links,
            "score": score
        })

    # 按权重分数从高到低排序，盲盒抽取前 5 强
    scored_events.sort(key=lambda x: x['score'], reverse=True)
    return scored_events[:5]

def save_daily_blind_box(events, now_obj):
    """将今日盲盒渲染成羊皮纸古典美学排版的独立精读页面"""
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
    """扫描归档目录，全自动编译出高颜值且带动态沙盒控制台的古典日历主枢纽"""
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
                                "title": "🔮 历史灵感盲盒已送达"
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
            --parchment-bg: #fdfaf4; 
            --parchment-border: #e6dfd3; 
            --ink-dark: #2a2421; 
            --ink-muted: #7c7066; 
            --imperial: #ff3b30; /* Adjusted to match reference image 1000121759.png red */
            --imperial-dark: #8c1d40;
            --card-bg: #ffffff;
        }
        body, html { 
            font-family: "Georgia", -apple-system, BlinkMacSystemFont, serif; 
            -webkit-font-smoothing: antialiased; 
            background: var(--parchment-bg); 
            margin: 0; padding: 0; color: var(--ink-dark); 
            height: 100%;
        }
        .app-layout { display: flex; flex-direction: column; height: 100%; }
        .header-panel { text-align: center; padding: 35px 20px 20px 20px; border-bottom: 1px dashed var(--parchment-border); }
        .header-panel h1 { font-size: 2.4rem; font-weight: normal; margin: 0 0 8px 0; font-style: italic; color: var(--imperial-dark); }
        .header-panel p { margin: 0; font-size: 0.85rem; letter-spacing: 2px; text-transform: uppercase; color: var(--ink-muted); }
        
        .main-content { flex: 1; overflow-y: auto; padding: 20px 15px; }
        .container { max-width: 600px; margin: 0 auto; }
        
        /* 日历控制条 */
        .cal-controls { display: flex; justify-content: center; align-items: center; gap: 12px; margin-bottom: 20px; }
        .cal-btn { background: var(--imperial-dark); color: #fff; border: none; border-radius: 6px; padding: 8px 14px; font-size: 14px; cursor: pointer; font-weight: bold; }
        .cal-btn:active { opacity: 0.8; transform: scale(0.96); }
        .select-shell { padding: 6px 12px; border: 1px solid var(--parchment-border); border-radius: 6px; font-size: 15px; background: #fff; font-family: inherit; font-weight: bold; outline: none; }
        
        /* 羊皮纸日历架构 */
        .calendar-box { background: var(--card-bg); border: 1px solid var(--parchment-border); border-radius: 14px; padding: 20px; box-shadow: 0 4px 15px rgba(0,0,0,0.02); margin-bottom: 25px; user-select: none; }
        .weekdays { display: grid; grid-template-columns: repeat(7, 1fr); text-align: center; font-weight: bold; font-size: 13px; color: var(--ink-muted); margin-bottom: 12px; padding-bottom: 8px; border-bottom: 1px solid #f5ebd9; }
        .days-grid { display: grid; grid-template-columns: repeat(7, 1fr); gap: 6px; }
        .day-cell { aspect-ratio: 1; display: flex; flex-direction: column; justify-content: center; align-items: center; font-size: 16px; font-weight: bold; border-radius: 8px; cursor: pointer; position: relative; transition: all 0.2s; }
        .day-cell.empty { visibility: hidden; }
        .day-cell.has-news { color: var(--ink-dark); }
        .day-cell.no-news { color: #d0c8be; }
        .day-cell.selected { background: #ffebeb; border: 1px solid var(--imperial); color: var(--imperial); }
        .day-cell.today { background: #f4ebd9; border: 1px solid var(--parchment-border); }
        .dot { width: 5px; height: 5px; background-color: var(--imperial); border-radius: 50%; position: absolute; bottom: 6px; display: none; }
        .day-cell.has-news .dot { display: block; }
        
        /* 盲盒抽取结果列表 (兼容双击删除UI) */
        .feed-list { display: flex; flex-direction: column; gap: 12px; }
        .feed-item-wrapper { display: flex; align-items: stretch; gap: 10px; width: 100%; transition: all 0.3s ease; }
        .feed-item { flex: 1; background: var(--card-bg); border: 1px solid var(--parchment-border); border-radius: 12px; padding: 18px; display: flex; justify-content: space-between; align-items: center; text-decoration: none; color: var(--ink-dark); box-shadow: 0 2px 8px rgba(0,0,0,0.01); border-left: 4px solid var(--imperial); min-width: 0; }
        .feed-item:active { transform: scale(0.99); background: #faf8f2; }
        .feed-time { font-size: 15px; font-weight: bold; color: var(--imperial); font-family: monospace; white-space: nowrap; }
        .feed-title { font-size: 14px; font-weight: bold; color: var(--ink-dark); margin-left: 15px; text-align: left; flex: 1; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; color: var(--imperial); }
        .empty-placeholder { text-align: center; padding: 40px 20px; color: var(--ink-muted); font-size: 14px; background: var(--card-bg); border: 1px dashed var(--parchment-border); border-radius: 12px; font-style: italic; }
        
        /* 独立删除按钮 */
        .delete-btn { display: none; width: 56px; background-color: #ff3b30; color: white; border: none; border-radius: 12px; font-size: 20px; cursor: pointer; align-items: center; justify-content: center; box-shadow: 0 2px 8px rgba(255,59,48,0.2); transition: transform 0.1s; flex-shrink: 0; }
        .delete-btn:active { transform: scale(0.92); }
        .delete-btn.show { display: flex; animation: slideIn 0.2s ease forwards; }
        
        @keyframes slideIn { from { opacity: 0; transform: translateX(10px); } to { opacity: 1; transform: translateX(0); } }
    </style>
</head>
<body>
    <div class="app-layout">
        <div class="header-panel">
            <h1>Echoes of History</h1>
            <p>~ 赛博档案馆 / 灵感随想枢纽 ~</p>
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

                <!-- 日历区域：双击/连按呼出删除模式 -->
                <div class="calendar-box" id="calendarBox">
                    <div class="weekdays"><span>一</span><span>二</span><span>三</span><span>四</span><span>五</span><span>六</span><span>日</span></div>
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
        let isDeleteMode = false; // 删除模式状态

        const yearSelect = document.getElementById('yearSelect');
        const monthSelect = document.getElementById('monthSelect');
        const daysGrid = document.getElementById('daysGrid');
        const feedList = document.getElementById('feedList');
        const calendarBox = document.getElementById('calendarBox');

        // ==== 移动端双击检测 ====
        let lastTapTime = 0;
        calendarBox.addEventListener('touchstart', function(e) {
            const currentTime = new Date().getTime();
            const tapLength = currentTime - lastTapTime;
            if (tapLength < 400 && tapLength > 0) {
                e.preventDefault(); 
                toggleDeleteMode();
            }
            lastTapTime = currentTime;
        }, {passive: false});
        
        // 兼容PC端双击
        calendarBox.addEventListener('dblclick', toggleDeleteMode);

        function toggleDeleteMode() {
            isDeleteMode = !isDeleteMode;
            renderBoxList(selectedYear, selectedMonth, selectedDay);
            if (isDeleteMode) {
                // 提供一点视觉反馈
                calendarBox.style.border = "1px solid #ff3b30";
                setTimeout(() => calendarBox.style.border = "", 300);
            }
        }

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
                dayData.forEach((item, index) => {
                    const wrapper = document.createElement('div');
                    wrapper.className = 'feed-item-wrapper';

                    const a = document.createElement('a'); 
                    a.href = item.path; 
                    a.className = 'feed-item';
                    
                    // 为了高度还原图片 1000121759.png 的文案样式
                    a.innerHTML = `<span class="feed-title">${item.title.replace('🔮 ', '')}</span>`;
                    
                    wrapper.appendChild(a);

                    if (isDeleteMode) {
                        const delBtn = document.createElement('button');
                        delBtn.className = 'delete-btn show';
                        delBtn.innerHTML = '🗑️'; // 也可以用SVG图标
                        delBtn.onclick = (e) => {
                            e.preventDefault();
                            handleDeleteItem(year, month, day, index, item.path);
                        };
                        wrapper.appendChild(delBtn);
                    }

                    feedList.appendChild(wrapper);
                });
            } else {
                feedList.innerHTML = '<div class="empty-placeholder">该日未开启虚空历史盲盒</div>';
            }
        }

        // ==== GitHub API 同步删除逻辑 ====
        async function handleDeleteItem(year, month, day, index, filePath) {
            if (!confirm("确定要删除这条记录并同步到 GitHub 吗？")) return;
            
            let token = localStorage.getItem('gh_token');
            let repo = localStorage.getItem('gh_repo');
            
            if (!token || !repo) {
                token = prompt("【首次设置】请输入 GitHub Personal Access Token (需包含 repo 权限):");
                if (!token) return;
                repo = prompt("请输入仓库地址 (格式: 用户名/仓库名，例如: zhangsan/history-box):");
                if (!repo) return;
                localStorage.setItem('gh_token', token);
                localStorage.setItem('gh_repo', repo);
            }

            // 根据 Python 脚本逻辑，文件位于 docs 目录下
            const targetRepoPath = `docs/${filePath}`;
            const url = `https://api.github.com/repos/${repo}/contents/${targetRepoPath}`;
            
            try {
                // 1. 获取文件的 SHA
                const getRes = await fetch(url, { headers: { 'Authorization': `token ${token}` } });
                
                if (getRes.status === 404) {
                    alert("文件在远程仓库中不存在，将在本地视图中直接移除。");
                    removeLocalData(year, month, day, index);
                    return;
                }
                
                if (!getRes.ok) throw new Error(await getRes.text());
                
                const fileData = await getRes.json();
                const sha = fileData.sha;

                // 2. 发起 DELETE 请求
                const delRes = await fetch(url, {
                    method: 'DELETE',
                    headers: {
                        'Authorization': `token ${token}`,
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        message: `Delete ${filePath} via Web UI`,
                        sha: sha
                    })
                });

                if (delRes.ok) {
                    alert("删除成功，并已同步到 GitHub！");
                    removeLocalData(year, month, day, index);
                } else {
                    alert("删除失败: " + await delRes.text());
                }
            } catch (e) {
                alert("请求出错: " + e.message);
                if(e.message.includes("Bad credentials")) {
                    localStorage.removeItem('gh_token');
                }
            }
        }

        function removeLocalData(year, month, day, index) {
            archiveData[year][month][day].splice(index, 1);
            if (archiveData[year][month][day].length === 0) {
                delete archiveData[year][month][day];
            }
            renderCalendarGrid(selectedYear, selectedMonth);
            renderBoxList(selectedYear, selectedMonth, selectedDay);
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

    # 自动获取今日维基百科快讯
    data = fetch_wikipedia_history(now.month, now.day)
    if data:
        best_events = extract_blind_box_events(data)
        if best_events:
            save_daily_blind_box(best_events, now)

    # 全自动刷新日历主视图索引
    generate_chronicle_hub()
