# 📜 Echoes of History Automatons

**Echoes of History** 是一个基于 GitHub Actions 的全自动历史灵感档案馆。它每天会自动从维基百科提取当日的历史事件，通过加权智能筛选，将最具戏剧冲突的 5 个事件封装为“历史盲盒”，并渲染成具有古典羊皮纸美学的精读页面。

---

## 🔮 项目逻辑 (The Core Mechanism)

本项目并非简单的信息搬运，而是一个为您提供创作灵感的自动化数字炼金术：

1.  **时间信道触发**：每天自动通过 `cron` 定时任务（UTC 15:00）或根据代码更新触发。
2.  **虚空盲盒提炼**：利用自定义的历史偏好算法（Weighting Algorithm），为 `roman`、`dynasty` 等关键词偏好的历史事件增加权重，确保提取的内容符合您的品味。
3.  **古典美学封印**：自动生成的 HTML 页面采用了响应式设计与仿古排版，并附带了 `灵感回响 (Inspiration Spark)` 模块，为您提供魔幻、悬疑、编年史架构等多维度的创作切入点。
4.  **沙盒枢纽控制台**：主页 `index.html` 内置了动态档案馆管理系统，支持日期索引导航，并集成 GitHub API 的本地配置中心，可直接在网页端销毁已不再需要的历史卷宗。

---

## 🛠 技术栈 (Stack)

* **Runtime**: Python 3.10
* **Automation**: GitHub Actions (Checkout, Setup-Python)
* **Data Source**: Wikipedia "On This Day" Open API
* **Frontend**: CSS Variables (Parchement Aesthetic), Vanilla JavaScript (No frameworks)
* **Integration**: GitHub REST API (自动提交与资源维护)

---

## 📜 如何启用 (Deployment)

1.  **Fork 本仓库**。
2.  在仓库 `Settings` -> `Secrets and variables` -> `Actions` 中，该项目已配置为直接通过 GitHub Actions 的 `GITHUB_TOKEN` 实现自动化归档（无需手动设置 Token 即可完成初始运行）。
3.  一旦推送 `fetch_history.py` 触发工作流，即刻开启时间长河。
4.  访问项目的 `https://your-username.github.io/your-repo-name/docs/` 即可进入档案馆。

---

## ⚙️ 本地配置中心 (Settings)

在档案馆首页点击右上角的 **⚙️ (齿轮图标)**，您可以输入您的 GitHub Personal Access Token。
* **安全性**：您的密钥仅存储在浏览器 `localStorage` 中，绝不会上传至任何第三方服务器。
* **功能**：配置后，您可以在网页上直接触发删除操作，联动删除 GitHub 仓库中的对应历史 HTML 文件。

---

## ✍️ 关于灵感 (Philosophy)

> "历史是编剧最伟大的素材库。当您感到思维枯竭时，开启一个随机的历史盲盒，让那个时代的余温为你点燃新的世界观碎片。"

---

*Powered by [moodHappy / HAL]*