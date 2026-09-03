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

# ================= 批注核心引擎 (JS) =================
ENGINE_SCRIPT = r"""
// XSS 安全隔离：对输入到 Markdown 的内容进行危险标签剥离
function renderMarkdown(text) {
    if (typeof marked === 'undefined') return text;
    let safeText = text.replace(/<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>/gi, '')
                       .replace(/<iframe\b[^<]*(?:(?!<\/iframe>)<[^<]*)*<\/iframe>/gi, '')
                       .replace(/\bon[a-z]+\s*=/gi, 'data-blocked=');
    return marked.parse(safeText);
}

let syncTimeout = null;
function scheduleSync() {
    const statusMsg = document.getElementById('sync-status');
    statusMsg.style.display = 'inline-block';
    statusMsg.style.backgroundColor = '#f39c12';
    statusMsg.innerText = '⏳ 更改已记录，5秒后自动同步...';
    statusMsg.style.cursor = 'default';
    statusMsg.onclick = null;

    if (syncTimeout) clearTimeout(syncTimeout);
    syncTimeout = setTimeout(syncToGitHub, 5000);
}

// === AI 解析核心逻辑 ===
const AI_PROMPT = `请分析以下英文段落，并严格按照以下 Markdown 格式输出（不要输出任何额外的废话）：\n\n### 📌 完整翻译\n\n[此处填写完整翻译]\n\n### 📌 Key Expressions\n\n- **[单词或短语]**\n  = [中文释义]\n  （[可选的补充说明，如倒装结构或语境等]）\n\n段落内容：\n`;

async function fetchGroq(text, apiKey, modelName) {
    const res = await fetch('https://api.groq.com/openai/v1/chat/completions', {
        method: 'POST',
        headers: {
            'Authorization': `Bearer ${apiKey}`,
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            model: modelName,
            messages: [
                { role: 'system', content: 'You are an English teacher. Output EXACTLY in the requested Markdown format.' },
                { role: 'user', content: AI_PROMPT + `"${text}"` }
            ],
            temperature: 0.3
        })
    });
    if (!res.ok) throw new Error(`Groq API Error: ${res.status}`);
    const json = await res.json();
    if (json.choices && json.choices.length > 0) return json.choices[0].message.content.trim();
    throw new Error('Groq返回数据异常');
}

async function fetchGLM(text, apiKey, modelName) {
    const res = await fetch('https://open.bigmodel.cn/api/paas/v4/chat/completions', {
        method: 'POST',
        headers: {
            'Authorization': `Bearer ${apiKey}`,
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            model: modelName,
            messages: [
                { role: 'system', content: 'You are an English teacher. Output EXACTLY in the requested Markdown format.' },
                { role: 'user', content: AI_PROMPT + `"${text}"` }
            ],
            temperature: 0.3
        })
    });
    if (!res.ok) throw new Error(`智谱GLM API Error: ${res.status}`);
    const json = await res.json();
    if (json.choices && json.choices.length > 0) return json.choices[0].message.content.trim();
    throw new Error('智谱GLM返回数据异常');
}

// 【新增】：全球/国内主流 AI 超级适配器 (OpenAI标准格式、Gemini、Claude原生接口)
async function fetchCustomAI(text, url, apiKey, modelName) {
    let headers = { 'Content-Type': 'application/json' };
    let bodyData = {};

    // 特殊适配 1: Anthropic Claude 官方原生 API
    if (url.includes('anthropic.com')) {
        headers['x-api-key'] = apiKey;
        headers['anthropic-version'] = '2023-06-01';
        headers['anthropic-dangerous-direct-browser-access'] = 'true';
        bodyData = {
            model: modelName,
            max_tokens: 2000,
            messages: [{ role: 'user', content: AI_PROMPT + `"${text}"` }]
        };
    }
    // 特殊适配 2: Google Gemini 官方原生 API
    else if (url.includes('generativelanguage.googleapis.com')) {
        let targetUrl = url;
        if (!targetUrl.includes('key=')) {
            targetUrl += (targetUrl.includes('?') ? '&' : '?') + 'key=' + apiKey;
        }
        const res = await fetch(targetUrl, {
            method: 'POST',
            headers: headers,
            body: JSON.stringify({
                contents: [{ parts: [{ text: AI_PROMPT + `"${text}"` }] }]
            })
        });
        if (!res.ok) throw new Error(`Gemini API Error: ${res.status}`);
        const json = await res.json();
        if (json.candidates && json.candidates[0]?.content?.parts[0]?.text) {
            return json.candidates[0].content.parts[0].text.trim();
        }
        throw new Error('Gemini 返回数据异常');
    }
    // 标准适配: 涵盖 OpenAI, DeepSeek, Kimi, 硅基流动, ChatAnywhere, OpenRouter 等
    else {
        headers['Authorization'] = 'Bearer ' + apiKey;
        bodyData = {
            model: modelName,
            messages: [
                { role: 'system', content: 'You are an English teacher. Output EXACTLY in the requested Markdown format.' },
                { role: 'user', content: AI_PROMPT + `"${text}"` }
            ],
            temperature: 0.3
        };
    }

    const res = await fetch(url, {
        method: 'POST',
        headers: headers,
        body: JSON.stringify(bodyData)
    });
    if (!res.ok) throw new Error(`自定义 AI 接口报错: ${res.status}`);
    const json = await res.json();
    if (json.content && Array.isArray(json.content) && json.content[0]?.text) {
        return json.content[0].text.trim();
    }
    if (json.choices && json.choices.length > 0) {
        return json.choices[0].message.content.trim();
    }
    throw new Error('自定义 AI 返回结构不符合预期');
}

async function executeAIPipeline(text) {
    const pref = localStorage.getItem('PREFERRED_AI') || 'custom';
    const groqKey = localStorage.getItem('GROQ_API_KEY') || '';
    const glmKey = localStorage.getItem('GLM_API_KEY') || '';
    const groqModel = localStorage.getItem('GROQ_MODEL') || '';
    const glmModel = localStorage.getItem('GLM_MODEL') || '';
    const customUrl = localStorage.getItem('CUSTOM_API_URL') || '';
    const customKey = localStorage.getItem('CUSTOM_API_KEY') || '';
    const customModel = localStorage.getItem('CUSTOM_MODEL') || '';

    const runGroq = async () => {
        if (!groqKey || !groqModel) throw new Error("Groq 配置不完整");
        return await fetchGroq(text, groqKey, groqModel);
    };
    const runGLM = async () => {
        if (!glmKey || !glmModel) throw new Error("智谱GLM 配置不完整");
        return await fetchGLM(text, glmKey, glmModel);
    };
    const runCustom = async () => {
        if (!customUrl || !customKey || !customModel) throw new Error("自定义 AI 配置不完整");
        return await fetchCustomAI(text, customUrl, customKey, customModel);
    };

    if (pref === 'custom') {
        try {
            return await runCustom();
        } catch (err) {
            console.warn("自定义 AI 失败，尝试降级:", err);
            if (groqKey && groqModel) {
                document.getElementById('sync-status').innerText = '⚠️ 自定义异常，正降级为Groq...';
                try { return await runGroq(); } catch(e2) { if (glmKey && glmModel) return await runGLM(); throw e2; }
            } else if (glmKey && glmModel) {
                document.getElementById('sync-status').innerText = '⚠️ 自定义异常，正降级为智谱...';
                return await runGLM();
            }
            throw err;
        }
    } else if (pref === 'groq') {
        try {
            return await runGroq();
        } catch (err) {
            console.warn("首选 Groq 失败，尝试降级:", err);
            if (glmKey && glmModel) {
                document.getElementById('sync-status').innerText = '⚠️ Groq异常，正降级为智谱...';
                return await runGLM();
            } else if (customUrl && customKey && customModel) {
                document.getElementById('sync-status').innerText = '⚠️ Groq异常，正降级为自定义AI...';
                return await runCustom();
            }
            throw err;
        }
    } else {
        try {
            return await runGLM();
        } catch (err) {
            console.warn("首选 智谱 失败，尝试降级:", err);
            if (groqKey && groqModel) {
                document.getElementById('sync-status').innerText = '⚠️ 智谱异常，正降级为Groq...';
                return await runGroq();
            } else if (customUrl && customKey && customModel) {
                document.getElementById('sync-status').innerText = '⚠️ 智谱异常，正降级为自定义AI...';
                return await runCustom();
            }
            throw err;
        }
    }
}

function initAnnotations() {
    document.querySelectorAll('.para-wrap').forEach(wrap => {
        const view = wrap.querySelector('.anno-view');
        const edit = wrap.querySelector('.anno-edit');
        const toggle = wrap.querySelector('.anno-toggle');
        const aiToggle = wrap.querySelector('.ai-toggle');
        const box = wrap.querySelector('.anno-box');

        const rawText = edit.value.trim();
        if (rawText) {
            toggle.classList.add('has-anno');
            view.innerHTML = renderMarkdown(rawText);
        }
        
        // --- AI 解析交互 ---
        if (aiToggle) {
            aiToggle.addEventListener('click', async (e) => {
                e.preventDefault();
                e.stopPropagation();
                if (aiToggle.classList.contains('loading')) return;

                const pref = localStorage.getItem('PREFERRED_AI') || 'custom';
                const groqKey = localStorage.getItem('GROQ_API_KEY') || '';
                const glmKey = localStorage.getItem('GLM_API_KEY') || '';
                const customUrl = localStorage.getItem('CUSTOM_API_URL') || '';
                const customKey = localStorage.getItem('CUSTOM_API_KEY') || '';
                
                let isReady = false;
                if (pref === 'custom' && customUrl && customKey) isReady = true;
                if (pref === 'groq' && groqKey) isReady = true;
                if (pref === 'glm' && glmKey) isReady = true;

                if (!isReady && !groqKey && !glmKey && !customKey) {
                    alert('⚠️ 请先返回【档案馆大厅】右上角的 ⚙️配置中心 设置 AI 接口与密钥！');
                    return;
                }

                // 提取纯文本，避开红点和机器人图标
                const pClone = wrap.querySelector('.card-text').cloneNode(true);
                pClone.querySelectorAll('.anno-toggle, .ai-toggle').forEach(el => el.remove());
                const pText = pClone.textContent.trim();
                if (!pText) return;

                aiToggle.classList.add('loading');
                const statusMsg = document.getElementById('sync-status');
                statusMsg.style.display = 'inline-block';
                statusMsg.style.backgroundColor = '#1a365d';
                statusMsg.innerText = '🤖 AI 思考中...';

                try {
                    const aiContent = await executeAIPipeline(pText);
                    
                    box.style.display = 'block';
                    view.style.display = 'none';
                    edit.style.display = 'block';
                    edit.value = aiContent;
                    
                    // 触发失焦，联动 Marked.js 渲染与 GitHub 自动保存
                    edit.focus();
                    edit.blur();
                    
                    statusMsg.style.backgroundColor = '#2ea44f';
                    statusMsg.innerText = '✅ AI 解析成功';
                    setTimeout(() => { if (statusMsg.innerText.includes('AI')) statusMsg.style.display = 'none'; }, 2000);
                } catch (err) {
                    console.error(err);
                    alert('❌ AI 解析失败: ' + err.message);
                    statusMsg.style.display = 'none';
                } finally {
                    aiToggle.classList.remove('loading');
                }
            });
        }

        // --- 原有红点交互 ---
        toggle.addEventListener('click', (e) => {
            e.preventDefault();
            e.stopPropagation();
            
            if (box.style.display === 'block') {
                box.style.display = 'none';
                wrap.scrollIntoView({ behavior: 'smooth', block: 'center' });
            } else {
                box.style.display = 'block';
                if (!edit.value.trim()) {
                    view.style.display = 'none';
                    edit.style.display = 'block';
                    setTimeout(() => edit.focus(), 50);
                } else {
                    view.style.display = 'block';
                    edit.style.display = 'none';
                }
            }
        });

        const triggerEdit = () => {
            view.style.display = 'none';
            edit.style.display = 'block';
            edit.value = edit.value;
            setTimeout(() => edit.focus(), 50);
        };

        view.addEventListener('dblclick', () => {
            box.style.display = 'none';
            wrap.scrollIntoView({ behavior: 'smooth', block: 'center' });
        });

        let lastTap = 0;
        view.addEventListener('touchstart', e => {
            if (e.touches.length === 2) {
                triggerEdit();
            } else if (e.touches.length === 1) {
                const currentTime = new Date().getTime();
                const tapLength = currentTime - lastTap;
                if (tapLength < 500 && tapLength > 0) {
                    box.style.display = 'none';
                    wrap.scrollIntoView({ behavior: 'smooth', block: 'center' });
                }
                lastTap = currentTime;
            }
        }, {passive: true});

        edit.addEventListener('blur', () => {
            const newVal = edit.value.trim();
            try { view.innerHTML = newVal ? renderMarkdown(newVal) : ''; } catch(e){}
            edit.style.display = 'none';

            if (newVal) {
                view.style.display = 'block';
                toggle.classList.add('has-anno');
            } else {
                view.style.display = 'none';
                box.style.display = 'none';
                toggle.classList.remove('has-anno');
            }

            if (edit.getAttribute('data-old-val') !== newVal) {
                edit.setAttribute('data-old-val', newVal);
                scheduleSync();
            }
        });
        edit.setAttribute('data-old-val', rawText);
    });
}
window.onload = initAnnotations;

// 核心修复：纯净重构逻辑，彻底抛弃可能被第三方插件污染的脏 DOM
function reconstructSelfHTML() {
    // 1. 同步输入内容到节点
    document.querySelectorAll('.anno-edit').forEach(edit => {
        edit.textContent = edit.value; 
    });

    // 2. 仅克隆安全、必要的核心模块，阻断浏览器插件脚本被意外吸入
    const navClone = document.querySelector('.nav-header').cloneNode(true);
    const containerClone = document.querySelector('.container').cloneNode(true);
    
    // 3. 清洗核心模块里的 UI 残留状态
    const statusMsg = navClone.querySelector('#sync-status');
    if(statusMsg) statusMsg.style.display = 'none';
    
    containerClone.querySelectorAll('.anno-box').forEach(box => box.style.display = 'none');
    containerClone.querySelectorAll('.anno-view').forEach(view => view.style.display = 'none');
    containerClone.querySelectorAll('.anno-edit').forEach(edit => edit.style.display = 'none');

    // 4. 提取原汁原味的自带 CSS 和自带 JS
    const styleText = document.querySelector('style').textContent;
    const engineText = document.getElementById('matrix-engine').textContent;

    // 5. 组装一个“无菌”的全新 HTML 字符串返回
    const cleanHTML = `<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>${document.title}</title>
    <script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"><\/script>
    <style>${styleText}</style>
</head>
<body>
    ${navClone.outerHTML}
    ${containerClone.outerHTML}
    <script id="matrix-engine">${engineText}<\/script>
</body>
</html>`;

    return cleanHTML;
}

async function syncToGitHub() {
    const token = localStorage.getItem('gh_token');
    const owner = localStorage.getItem('gh_user');
    const repo = localStorage.getItem('gh_repo');
    
    if(!token || !owner || !repo) {
        alert('缺少 GitHub Token 或配置，无法同步批注！请先在日历大厅右上角配置。');
        return;
    }

    const statusMsg = document.getElementById('sync-status');
    statusMsg.style.display = 'inline-block';
    statusMsg.style.backgroundColor = '#2ea44f';
    statusMsg.innerText = '📡 同步中...';

    const pureHtml = reconstructSelfHTML();
    
    let urlPath = window.location.pathname;
    const match = urlPath.match(/(\d{4}\/\d{1,2}\/[^/]+\.html)$/);
    let fileRelPath = match ? "docs/" + match[1] : (urlPath.includes('docs/') ? urlPath.substring(urlPath.indexOf('docs/')) : null);
    
    if (!fileRelPath) {
        alert('文件路径解析失败，无法同步！');
        statusMsg.style.display = 'none';
        return;
    }

    try {
        const base64Html = btoa(encodeURIComponent(pureHtml).replace(/%([0-9A-F]{2})/g, function(match, p1) {
            return String.fromCharCode('0x' + p1);
        }));

        const getRes = await fetch(`https://api.github.com/repos/${owner}/${repo}/contents/${fileRelPath}?t=${Date.now()}`, {
            headers: { 'Authorization': `token ${token}` },
            cache: 'no-store'
        });

        if (!getRes.ok) throw new Error('API 获取 SHA 失败');
        const fileData = await getRes.json();

        const putRes = await fetch(`https://api.github.com/repos/${owner}/${repo}/contents/${fileRelPath}`, {
            method: 'PUT',
            headers: { 'Authorization': `token ${token}`, 'Content-Type': 'application/json' },
            body: JSON.stringify({ message: `Auto-save annotation for Blind Box`, content: base64Html, sha: fileData.sha })
        });

        if(putRes.ok) {
            statusMsg.style.backgroundColor = '#2ea44f';
            statusMsg.innerText = '✅ 云端已同步';
            setTimeout(() => {
                if (statusMsg.innerText === '✅ 云端已同步') {
                    statusMsg.style.display = 'none';
                }
            }, 3000);
        } else {
            throw new Error('Put 请求失败');
        }
    } catch(e) {
        console.error(e);
        statusMsg.style.backgroundColor = '#e74c3c';
        statusMsg.innerText = '❌ 同步失败 (点击重试)';
        statusMsg.style.cursor = 'pointer';
        statusMsg.onclick = () => {
            statusMsg.onclick = null;
            statusMsg.style.cursor = 'default';
            syncToGitHub();
        };
    }
}
"""
# ==================================================

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
            <div class="para-wrap">
                <!-- 在这里注入了 AI 智能解析机器人按钮 -->
                <p class="card-text">{ev['text']}<span class="anno-toggle" title="点击添加/查看批注">🔴</span><span class="ai-toggle" title="AI智能解析">🤖</span></p>
                <div class="anno-box" style="display:none;">
                    <div class="anno-view markdown-body"></div>
                    <textarea class="anno-edit" style="display:none;" placeholder="在此记录有关该历史事件的灵感或设定..."></textarea>
                </div>
            </div>
            {links_html}
            <div class="inspiration-box">
                <div class="prompt-title">📝 灵感回响 (Inspiration Spark)</div>
                <div class="prompt-body">{inspiration_prompt}</div>
            </div>
        </div>
        """

    html_content = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>Echoes of History - Blind Box</title>
    <script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
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
        .header-right {{ display: flex; align-items: center; gap: 12px; }}
        
        .sync-status {{ padding: 4px 10px; border-radius: 12px; font-size: 0.75rem; font-weight: bold; display: none; color: #fff; box-shadow: 0 2px 6px rgba(0,0,0,0.1); font-family: -apple-system, sans-serif; }}

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
        
        .para-wrap {{ position: relative; margin-bottom: 18px; }}
        .card-text {{ font-size: 1.15rem; color: var(--ink-dark); margin: 0; text-align: justify; line-height: 1.6; }}
        
        .anno-toggle, .ai-toggle {{ 
            display: inline-block; 
            margin-left: 8px; 
            cursor: pointer; 
            opacity: 0.3; 
            font-size: 0.85rem; 
            vertical-align: baseline; 
            transition: all 0.2s; 
            user-select: none; 
            padding: 6px 6px; 
            margin-top: -6px;
            margin-bottom: -6px;
            border-radius: 6px;
            touch-action: manipulation; 
            -webkit-tap-highlight-color: transparent; 
        }}
        .anno-toggle:hover, .anno-toggle:active, .ai-toggle:hover, .ai-toggle:active {{ opacity: 0.8; transform: scale(1.1); }}
        .anno-toggle.has-anno {{ opacity: 1; }}
        .ai-toggle.loading::after {{ content: "⏳"; display: inline-block; animation: spin 1s linear infinite; }}
        @keyframes spin {{ 100% {{ transform: rotate(360deg); }} }}

        .anno-box {{ display: none; margin-top: 12px; background: #fdfbf7; border-left: 4px solid var(--imperial-blue); padding: 12px 16px; border-radius: 0 6px 6px 0; box-shadow: 0 2px 8px rgba(0,0,0,0.02); }}
        .anno-view {{ font-size: 1.05rem; line-height: 1.6; color: var(--ink-dark); min-height: 24px; }}
        .anno-edit {{ width: 100%; min-height: 100px; padding: 10px; font-family: monospace; font-size: 0.95rem; border: 1px dashed var(--parchment-border); border-radius: 6px; box-sizing: border-box; resize: vertical; display: none; background: #fff; color: #333; outline: none; }}
        .anno-edit:focus {{ border: 1px solid var(--imperial-blue); box-shadow: 0 0 0 3px rgba(26,54,93,0.1); }}
        
        .markdown-body p {{ margin-top: 0; margin-bottom: 8px; }}
        .markdown-body p:last-child {{ margin-bottom: 0; }}
        .markdown-body p:empty {{ display: none; }}
        .markdown-body h1, .markdown-body h2, .markdown-body h3 {{ color: var(--imperial-blue); font-size: 1.15rem; margin: 10px 0 8px 0; border-bottom: 1px dashed var(--parchment-border); padding-bottom: 4px; }}
        .markdown-body ul, .markdown-body ol {{ margin: 0 0 8px 0; padding-left: 20px; }}
        .markdown-body blockquote {{ margin: 0 0 10px 0; padding: 10px 15px; background: rgba(26,54,93,0.05); border-left: 4px solid var(--imperial-blue); color: var(--ink-muted); }}

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
        <a href="../../index.html">📜 返回档案馆</a>
        <div class="header-right">
            <span class="sync-status" id="sync-status">📡 同步中...</span>
            <span style="font-size:0.9rem; color:var(--ink-muted); font-family:sans-serif;">{now_obj.strftime('%Y-%m-%d')}</span>
        </div>
    </div>
    <div class="container">
        <div class="box-title">
            <h1>Echoes of History</h1>
            <p>~ 今日份虚空历史盲盒 ~</p>
        </div>
        {events_html}
    </div>
    <script id="matrix-engine">###ENGINE_SCRIPT_PLACEHOLDER###</script>
</body>
</html>"""

    html_content = html_content.replace("###ENGINE_SCRIPT_PLACEHOLDER###", ENGINE_SCRIPT)

    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html_content)
    print(f"🎉 盲盒卷宗已封印入库，批注引擎已加载: {html_path}")
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
                                "title": "🔮 历史灵感盲盒已送达"
                            })
                    except: pass

    json_data = json.dumps(archive_data)

    html_template = r"""<!DOCTYPE html>
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
            --imperial: #ff3b30; 
            --imperial-dark: #8c1d40;
            --card-bg: #ffffff;
            --theme-blue: #1a365d;
        }
        * { box-sizing: border-box; }
        body, html { 
            font-family: "Georgia", -apple-system, BlinkMacSystemFont, serif; 
            -webkit-font-smoothing: antialiased; 
            background: var(--parchment-bg); 
            margin: 0; padding: 0; color: var(--ink-dark); 
            height: 100%;
        }
        .app-layout { display: flex; flex-direction: column; height: 100%; }
        
        .header-panel { text-align: center; padding: 35px 20px 20px 20px; border-bottom: 1px dashed var(--parchment-border); position: relative; }
        .header-panel h1 { font-size: 2.4rem; font-weight: normal; margin: 0 0 8px 0; font-style: italic; color: var(--imperial-dark); }
        .header-panel p { margin: 0; font-size: 0.85rem; letter-spacing: 2px; text-transform: uppercase; color: var(--ink-muted); }
        
        .settings-btn { position: absolute; top: 25px; right: 25px; font-size: 24px; cursor: pointer; color: #888; transition: transform 0.3s ease, color 0.2s; user-select: none; }
        .settings-btn:active, .settings-btn:hover { transform: rotate(90deg); color: #555; }

        .main-content { flex: 1; overflow-y: auto; padding: 20px 15px; }
        .container { max-width: 600px; margin: 0 auto; }
        
        .cal-controls { display: flex; justify-content: center; align-items: center; gap: 12px; margin-bottom: 20px; }
        .cal-btn { background: var(--theme-blue); color: #fff; border: none; border-radius: 8px; padding: 8px 14px; font-size: 14px; cursor: pointer; font-weight: bold; transition: all 0.2s; }
        .cal-btn:active { opacity: 0.8; transform: scale(0.96); }
        .select-shell { padding: 6px 12px; border: 1px solid var(--parchment-border); border-radius: 8px; font-size: 15px; background: #fff; font-family: inherit; font-weight: bold; outline: none; }
        
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
        
        .feed-list { display: flex; flex-direction: column; gap: 12px; }
        .feed-item-wrapper { display: flex; align-items: stretch; gap: 10px; width: 100%; transition: all 0.3s ease; }
        .feed-item { flex: 1; background: var(--card-bg); border: 1px solid var(--parchment-border); border-radius: 12px; padding: 18px; display: flex; justify-content: space-between; align-items: center; text-decoration: none; color: var(--ink-dark); box-shadow: 0 2px 8px rgba(0,0,0,0.01); border-left: 4px solid var(--imperial); min-width: 0; }
        .feed-item:active { transform: scale(0.99); background: #faf8f2; }
        .feed-title { font-size: 14px; font-weight: bold; margin-left: 15px; text-align: left; flex: 1; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; color: var(--imperial); }
        .empty-placeholder { text-align: center; padding: 40px 20px; color: var(--ink-muted); font-size: 14px; background: var(--card-bg); border: 1px dashed var(--parchment-border); border-radius: 12px; font-style: italic; }
        
        .delete-btn { display: none; width: 56px; background-color: #ff3b30; color: white; border: none; border-radius: 12px; font-size: 20px; cursor: pointer; align-items: center; justify-content: center; box-shadow: 0 2px 8px rgba(255,59,48,0.2); transition: transform 0.1s; flex-shrink: 0; }
        .delete-btn:active { transform: scale(0.92); }
        .delete-btn.show { display: flex; animation: slideIn 0.2s ease forwards; }
        
        @keyframes slideIn { from { opacity: 0; transform: translateX(10px); } to { opacity: 1; transform: translateX(0); } }

        .modal-overlay { display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0, 0, 0, 0.45); z-index: 1000; justify-content: center; align-items: center; backdrop-filter: blur(4px); }
        .modal-overlay.show { display: flex; animation: fadeInModal 0.2s; }
        
        .modal-box { background: #fff; width: 92%; max-width: 440px; max-height: 88vh; overflow-y: auto; border-radius: 16px; padding: 24px; box-shadow: 0 10px 30px rgba(0,0,0,0.15); font-family: -apple-system, BlinkMacSystemFont, sans-serif; }
        .modal-title { font-size: 18px; font-weight: bold; color: #222; margin: 0 0 4px 0; }
        .modal-subtitle { font-size: 12px; color: #777; margin-bottom: 18px; line-height: 1.5; }
        
        .section-card { background: #fbf9f6; border: 1px solid #eee5d8; border-radius: 10px; padding: 12px; margin-bottom: 14px; }
        .section-title { font-size: 12px; font-weight: bold; color: var(--theme-blue); margin-bottom: 10px; }
        
        .form-group { margin-bottom: 12px; }
        .form-group:last-child { margin-bottom: 0; }
        .form-group label { display: block; font-size: 11.5px; color: #555; margin-bottom: 5px; font-weight: bold; }
        .form-row { display: grid; grid-template-columns: repeat(auto-fit, minmax(170px, 1fr)); gap: 10px; }
        .form-group input, .form-group select { width: 100%; box-sizing: border-box; padding: 10px; border: 1px solid #ddd; border-radius: 8px; font-size: 13px; outline: none; transition: all 0.2s; background: #fff; }
        .form-group select { appearance: none; -webkit-appearance: none; background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='16' height='16' viewBox='0 0 24 24' fill='none' stroke='%2364748b' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpolyline points='6 9 12 15 18 9'%3E%3C/polyline%3E%3C/svg%3E"); background-repeat: no-repeat; background-position: right 10px center; padding-right: 32px; cursor: pointer; }
        .form-group input:focus, .form-group select:focus { border-color: var(--theme-blue); box-shadow: 0 0 0 2px rgba(26,54,93,0.1); }
        
        .modal-actions { display: flex; justify-content: flex-end; gap: 10px; margin-top: 20px; position: sticky; bottom: -24px; background: #fff; padding-top: 12px; border-top: 1px solid #eee; }
        .modal-btn { padding: 9px 18px; border-radius: 8px; font-size: 13.5px; font-weight: bold; cursor: pointer; border: none; transition: opacity 0.2s; }
        .btn-cancel { background: #f0f0f0; color: #444; }
        .btn-save { background: var(--theme-blue); color: #fff; }
        .btn-cancel:active { background: #e4e4e4; }
        .btn-save:active { opacity: 0.9; }
        
        @keyframes fadeInModal { from { opacity: 0; transform: scale(0.95); } to { opacity: 1; transform: scale(1); } }
    </style>
</head>
<body>
    <div class="app-layout">
        <div class="header-panel">
            <div class="settings-btn" id="btnSettings" title="本地配置中心">⚙️</div>
            <h1>Echoes of History</h1>
            <p>~ 赛博档案馆 / 灵感随想枢纽 ~</p>
        </div>
        
        <div class="main-content">
            <div class="container">
                <div class="cal-controls">
                    <button class="cal-btn" id="prevBtn">&lt;</button>
                    <select class="select-shell" id="yearSelect"></select>
                    <select class="select-shell" id="monthSelect"></select>
                    <button class="cal-btn" id="nextBtn">&gt;</button>
                    <button class="cal-btn" id="todayBtn">回到今天</button>
                </div>

                <div class="calendar-box" id="calendarBox">
                    <div class="weekdays"><span>一</span><span>二</span><span>三</span><span>四</span><span>五</span><span>六</span><span>日</span></div>
                    <div class="days-grid" id="daysGrid"></div>
                </div>

                <div class="feed-list" id="feedList"></div>
            </div>
        </div>
    </div>

    <!-- 现代美观本地配置 Modal -->
    <div class="modal-overlay" id="configModal">
        <div class="modal-box">
            <h2 class="modal-title">⚙️ 核心配置中心</h2>
            <p class="modal-subtitle">所有密钥均安全储存在浏览器本地（LocalStorage），无云端泄露风险。</p>
            
            <!-- GitHub 同步配置 -->
            <div class="section-card">
                <div class="section-title">🐙 GitHub 仓库同步</div>
                <div class="form-group">
                    <label>Personal Access Token</label>
                    <input type="password" id="inputToken" placeholder="ghp_xxxxxxxxxxxxxxxxxxxx">
                </div>
                <div class="form-row">
                    <div class="form-group">
                        <label>GitHub 用户名</label>
                        <input type="text" id="inputUser" placeholder="如: moodHappy">
                    </div>
                    <div class="form-group">
                        <label>GitHub 仓库名</label>
                        <input type="text" id="inputRepo" placeholder="如: echoes-history">
                    </div>
                </div>
            </div>

            <!-- 首选引擎设置 -->
            <div class="form-group">
                <label>首选 AI 引擎 (失败自动无缝降级)</label>
                <select id="inputPrefAI">
                    <option value="custom">🌐 自定义 AI (兼容OpenAI格式 / Gemini / Claude)</option>
                    <option value="groq">Groq</option>
                    <option value="glm">智谱 (GLM)</option>
                </select>
            </div>

            <!-- 自定义 AI 配置面板 -->
            <div class="section-card">
                <div class="section-title">🔌 自定义 AI 接口配置</div>
                <div class="form-group">
                    <label>API Endpoint (包含完整 URL 路径)</label>
                    <input type="text" id="inputCustomUrl" placeholder="如: https://api.openai.com/v1/chat/completions">
                </div>
                <div class="form-row">
                    <div class="form-group">
                        <label>API Key</label>
                        <input type="password" id="inputCustomKey" placeholder="sk-xxxxxx">
                    </div>
                    <div class="form-group">
                        <label>模型名称</label>
                        <input type="text" id="inputCustomModel" placeholder="如: gpt-4o-mini">
                    </div>
                </div>
            </div>
            
            <!-- Groq 配置 -->
            <div class="section-card">
                <div class="section-title">⚡ Groq 引擎配置</div>
                <div class="form-row">
                    <div class="form-group">
                        <label>Groq API Key</label>
                        <input type="password" id="inputGroq" placeholder="gsk_xxxxxxxxxx">
                    </div>
                    <div class="form-group">
                        <label>模型名称</label>
                        <input type="text" id="inputGroqModel" placeholder="如: llama-3.3-70b-versatile">
                    </div>
                </div>
            </div>

            <!-- 智谱 GLM 配置 -->
            <div class="section-card">
                <div class="section-title">🇨🇳 智谱 GLM 配置</div>
                <div class="form-row">
                    <div class="form-group">
                        <label>智谱 API Key</label>
                        <input type="password" id="inputGLM" placeholder="填写智谱 API Key">
                    </div>
                    <div class="form-group">
                        <label>模型名称</label>
                        <input type="text" id="inputGLMModel" placeholder="如: glm-4-flash">
                    </div>
                </div>
            </div>
            
            <div class="modal-actions">
                <button class="modal-btn btn-cancel" id="btnCancel">取消</button>
                <button class="modal-btn btn-save" id="btnSave">保存配置</button>
            </div>
        </div>
    </div>

    <script>
        // ===DATA_START===
        let archiveData = {REPLACEME_JSON_DATA};
        // ===DATA_END===
        
        const deletedPaths = JSON.parse(localStorage.getItem('deleted_paths') || '[]');
        for (let y in archiveData) {
            for (let m in archiveData[y]) {
                for (let d in archiveData[y][m]) {
                    archiveData[y][m][d] = archiveData[y][m][d].filter(item => !deletedPaths.includes(item.path));
                    if (archiveData[y][m][d].length === 0) delete archiveData[y][m][d];
                }
                if (Object.keys(archiveData[y][m]).length === 0) delete archiveData[y][m];
            }
            if (Object.keys(archiveData[y]).length === 0) delete archiveData[y];
        }

        const today = new Date();
        let selectedYear = today.getFullYear();
        let selectedMonth = today.getMonth() + 1;
        let selectedDay = today.getDate();
        let isDeleteMode = false;

        const yearSelect = document.getElementById('yearSelect');
        const monthSelect = document.getElementById('monthSelect');
        const daysGrid = document.getElementById('daysGrid');
        const feedList = document.getElementById('feedList');
        const calendarBox = document.getElementById('calendarBox');

        const configModal = document.getElementById('configModal');
        const btnSettings = document.getElementById('btnSettings');
        const btnCancel = document.getElementById('btnCancel');
        const btnSave = document.getElementById('btnSave');
        
        const inputToken = document.getElementById('inputToken');
        const inputUser = document.getElementById('inputUser');
        const inputRepo = document.getElementById('inputRepo');
        const inputPrefAI = document.getElementById('inputPrefAI');
        const inputCustomUrl = document.getElementById('inputCustomUrl');
        const inputCustomKey = document.getElementById('inputCustomKey');
        const inputCustomModel = document.getElementById('inputCustomModel');
        const inputGroq = document.getElementById('inputGroq');
        const inputGLM = document.getElementById('inputGLM');
        const inputGroqModel = document.getElementById('inputGroqModel');
        const inputGLMModel = document.getElementById('inputGLMModel');

        function openConfigModal() {
            inputToken.value = localStorage.getItem('gh_token') || '';
            inputUser.value = localStorage.getItem('gh_user') || '';
            inputRepo.value = localStorage.getItem('gh_repo') || '';
            inputPrefAI.value = localStorage.getItem('PREFERRED_AI') || 'custom';
            inputCustomUrl.value = localStorage.getItem('CUSTOM_API_URL') || '';
            inputCustomKey.value = localStorage.getItem('CUSTOM_API_KEY') || '';
            inputCustomModel.value = localStorage.getItem('CUSTOM_MODEL') || '';
            inputGroq.value = localStorage.getItem('GROQ_API_KEY') || '';
            inputGLM.value = localStorage.getItem('GLM_API_KEY') || '';
            inputGroqModel.value = localStorage.getItem('GROQ_MODEL') || '';
            inputGLMModel.value = localStorage.getItem('GLM_MODEL') || '';
            configModal.classList.add('show');
        }

        btnSettings.addEventListener('click', openConfigModal);
        btnCancel.addEventListener('click', () => { configModal.classList.remove('show'); });

        configModal.addEventListener('click', (e) => {
            if (e.target === configModal) configModal.classList.remove('show');
        });

        btnSave.addEventListener('click', () => {
            localStorage.setItem('gh_token', inputToken.value.trim());
            localStorage.setItem('gh_user', inputUser.value.trim());
            localStorage.setItem('gh_repo', inputRepo.value.trim());
            localStorage.setItem('PREFERRED_AI', inputPrefAI.value);
            localStorage.setItem('CUSTOM_API_URL', inputCustomUrl.value.trim());
            localStorage.setItem('CUSTOM_API_KEY', inputCustomKey.value.trim());
            localStorage.setItem('CUSTOM_MODEL', inputCustomModel.value.trim());
            localStorage.setItem('GROQ_API_KEY', inputGroq.value.trim());
            localStorage.setItem('GLM_API_KEY', inputGLM.value.trim());
            localStorage.setItem('GROQ_MODEL', inputGroqModel.value.trim());
            localStorage.setItem('GLM_MODEL', inputGLMModel.value.trim());
            configModal.classList.remove('show');
            alert('配置已成功保存在本地！');
        });

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
        
        calendarBox.addEventListener('dblclick', toggleDeleteMode);

        function toggleDeleteMode() {
            isDeleteMode = !isDeleteMode;
            renderBoxList(selectedYear, selectedMonth, selectedDay);
            if (isDeleteMode) {
                calendarBox.style.border = "1px solid #ff3b30";
                setTimeout(() => calendarBox.style.border = "1px solid var(--parchment-border)", 300);
            }
        }

        function initDropdowns() {
            yearSelect.innerHTML = '';
            const currentY = today.getFullYear();
            
            for (let y = currentY; y <= currentY + 50; y++) {
                const opt = document.createElement('option'); 
                opt.value = y; 
                opt.textContent = y + ' 年';
                yearSelect.appendChild(opt);
            }
            
            let availableYears = Array.from(yearSelect.options).map(o => parseInt(o.value));
            if (!availableYears.includes(selectedYear)) selectedYear = currentY;
            yearSelect.value = selectedYear;

            updateMonthDropdown(selectedYear);
        }

        function updateMonthDropdown(year) {
            monthSelect.innerHTML = '';
            for (let m = 1; m <= 12; m++) {
                const opt = document.createElement('option'); 
                opt.value = m; 
                opt.textContent = String(m).padStart(2, '0') + '月';
                monthSelect.appendChild(opt);
            }
            monthSelect.value = selectedMonth;
            
            const daysInMonth = new Date(year, selectedMonth, 0).getDate();
            if (selectedDay > daysInMonth) selectedDay = daysInMonth;
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
                    
                    a.innerHTML = `<span class="feed-title">${item.title.replace('🔮 ', '')}</span>`;
                    
                    wrapper.appendChild(a);

                    if (isDeleteMode) {
                        const delBtn = document.createElement('button');
                        delBtn.className = 'delete-btn show';
                        delBtn.innerHTML = '🗑️';
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

        async function syncIndexHtmlToGithub(token, user, repoName) {
            const repo = `${user}/${repoName}`;
            const indexPath = `docs/index.html`;
            const url = `https://api.github.com/repos/${repo}/contents/${indexPath}`;
            try {
                const getRes = await fetch(url, { headers: { 'Authorization': `token ${token}` } });
                if (!getRes.ok) return;
                const fileData = await getRes.json();
                
                const rawContent = fileData.content.replace(/\s/g, '');
                let content = decodeURIComponent(Array.prototype.map.call(atob(rawContent), function(c) {
                    return '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2);
                }).join(''));
                
                const newJson = JSON.stringify(archiveData);
                content = content.replace(/\/\/ ===DATA_START===[\s\S]*?\/\/ ===DATA_END===/, `// ===DATA_START===\n        let archiveData = ${newJson};\n        // ===DATA_END===`);
                
                const newContentBase64 = btoa(encodeURIComponent(content).replace(/%([0-9A-F]{2})/g, function(match, p1) {
                    return String.fromCharCode('0x' + p1);
                }));

                await fetch(url, {
                    method: 'PUT',
                    headers: { 'Authorization': `token ${token}`, 'Content-Type': 'application/json' },
                    body: JSON.stringify({ message: `Auto-update index.html map after deletion`, content: newContentBase64, sha: fileData.sha })
                });
            } catch (e) {
                console.error("同步 index.html 失败:", e);
            }
        }

        async function handleDeleteItem(year, month, day, index, filePath) {
            if (!confirm("确定要彻底销毁这篇历史盲盒吗？")) return;
            
            let token = localStorage.getItem('gh_token');
            let user = localStorage.getItem('gh_user');
            let repoName = localStorage.getItem('gh_repo');
            
            if (!token || !user || !repoName) {
                alert("缺少 GitHub 配置，请先在本地配置中心（右上角齿轮 ⚙️）进行设置。");
                openConfigModal();
                return;
            }

            const repo = `${user}/${repoName}`;
            const targetRepoPath = `docs/${filePath}`;
            const url = `https://api.github.com/repos/${repo}/contents/${targetRepoPath}`;
            
            try {
                const getRes = await fetch(url, { headers: { 'Authorization': `token ${token}` } });
                
                if (getRes.status === 404) {
                    markAsDeletedLocally(filePath, year, month, day, index);
                    return;
                }
                
                if (!getRes.ok) throw new Error(await getRes.text());
                const fileData = await getRes.json();

                const delRes = await fetch(url, {
                    method: 'DELETE',
                    headers: { 'Authorization': `token ${token}`, 'Content-Type': 'application/json' },
                    body: JSON.stringify({ message: `Delete ${filePath} via Web UI`, sha: fileData.sha })
                });

                if (delRes.ok) {
                    markAsDeletedLocally(filePath, year, month, day, index);
                    syncIndexHtmlToGithub(token, user, repoName);
                } else {
                    alert("删除失败: " + await delRes.text());
                }
            } catch (e) {
                alert("请求出错: " + e.message);
            }
        }

        function markAsDeletedLocally(filePath, year, month, day, index) {
            if (!deletedPaths.includes(filePath)) {
                deletedPaths.push(filePath);
                localStorage.setItem('deleted_paths', JSON.stringify(deletedPaths));
            }
            archiveData[year][month][day].splice(index, 1);
            if (archiveData[year][month][day].length === 0) delete archiveData[year][month][day];
            if (Object.keys(archiveData[year][month] || {}).length === 0) delete archiveData[year][month];
            if (Object.keys(archiveData[year] || {}).length === 0) delete archiveData[year];
            
            initDropdowns(); 
            renderCalendarGrid(selectedYear, selectedMonth);
            renderBoxList(selectedYear, selectedMonth, selectedDay);
        }

        yearSelect.addEventListener('change', (e) => { 
            selectedYear = parseInt(e.target.value); 
            updateMonthDropdown(selectedYear);
            renderCalendarGrid(selectedYear, selectedMonth); 
            renderBoxList(selectedYear, selectedMonth, selectedDay); 
        });
        
        monthSelect.addEventListener('change', (e) => { 
            selectedMonth = parseInt(e.target.value); 
            const daysInMonth = new Date(selectedYear, selectedMonth, 0).getDate();
            if (selectedDay > daysInMonth) selectedDay = daysInMonth;
            renderCalendarGrid(selectedYear, selectedMonth); 
            renderBoxList(selectedYear, selectedMonth, selectedDay); 
        });
        
        document.getElementById('prevBtn').addEventListener('click', () => { 
            selectedMonth--;
            if (selectedMonth < 1) {
                selectedMonth = 12;
                selectedYear--;
                if (selectedYear < today.getFullYear()) {
                    selectedYear = today.getFullYear();
                    selectedMonth = 1;
                }
                yearSelect.value = selectedYear;
            }
            monthSelect.value = selectedMonth;
            
            const daysInMonth = new Date(selectedYear, selectedMonth, 0).getDate();
            if (selectedDay > daysInMonth) selectedDay = daysInMonth;
            
            renderCalendarGrid(selectedYear, selectedMonth); 
            renderBoxList(selectedYear, selectedMonth, selectedDay);
        });
        
        document.getElementById('nextBtn').addEventListener('click', () => { 
            selectedMonth++;
            if (selectedMonth > 12) {
                selectedMonth = 1;
                selectedYear++;
                yearSelect.value = selectedYear;
            }
            monthSelect.value = selectedMonth;
            
            const daysInMonth = new Date(selectedYear, selectedMonth, 0).getDate();
            if (selectedDay > daysInMonth) selectedDay = daysInMonth;
            
            renderCalendarGrid(selectedYear, selectedMonth); 
            renderBoxList(selectedYear, selectedMonth, selectedDay);
        });
        
        document.getElementById('todayBtn').addEventListener('click', () => { 
            selectedYear = today.getFullYear(); 
            selectedMonth = today.getMonth() + 1; 
            selectedDay = today.getDate(); 
            
            yearSelect.value = selectedYear;
            monthSelect.value = selectedMonth;
            
            renderCalendarGrid(selectedYear, selectedMonth); 
            renderBoxList(selectedYear, selectedMonth, selectedDay); 
        });

        initDropdowns(); 
        renderCalendarGrid(selectedYear, selectedMonth); 
        renderBoxList(selectedYear, selectedMonth, selectedDay);
    </script>
</body>
</html>"""

    final_html = html_template.replace("{REPLACEME_JSON_DATA}", json_data)
    with open(os.path.join(BASE_DIR, "index.html"), "w", encoding="utf-8") as f:
        f.write(final_html)
    print("🚀 主轴编年史大厅 index.html 编译同步完成！")

if __name__ == "__main__":
    os.makedirs(BASE_DIR, exist_ok=True)

    nojekyll_path = os.path.join(BASE_DIR, ".nojekyll")
    if not os.path.exists(nojekyll_path):
        with open(nojekyll_path, "w") as f:
            pass
        print("🛡️ 已自动生成 .nojekyll 防护盾，免除 GitHub Pages 报红叉！")

    now = datetime.now(tz_utc_8)

    data = fetch_wikipedia_history(now.month, now.day)
    if data:
        best_events = extract_blind_box_events(data)
        if best_events:
            save_daily_blind_box(best_events, now)

    generate_chronicle_hub()