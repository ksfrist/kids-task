# 小星星任务宝

一年级小学生任务激励系统 - 移动端 H5 + Flask 后端

## 一句话介绍
通过"即时贴纸奖励 + 星星币收集"帮助6-7岁孩子养成好习惯。

## 技术栈
- **后端**：Flask + SQLite（可切换 MySQL）
- **前端**：纯 HTML/CSS/JS（移动端 H5，无需安装）
- **部署**：Railway / 任意 Python 云服务器

## 快速启动（本地）

```bash
cd backend
pip install flask
python app.py
# 访问 http://localhost:5000
```

## API 文档

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /auth/register | 注册家庭（家长） |
| POST | /auth/login | 登录 |
| GET | /child/profile | 孩子主页（余额/贴纸/徽章） |
| GET/POST | /tasks | 任务列表/创建 |
| POST | /tasks/{id}/submit | 孩子提交完成 |
| POST | /tasks/{id}/approve | 家长审核通过 |
| GET | /rewards/catalog | 奖励规则 |
| GET | /stats/weekly | 本周统计 |

## 激励机制

- ⭐ 难度1 → 3星星币
- ⭐⭐ 难度2 → 5星星币
- ⭐⭐⭐ 难度3 → 8星星币
- ⭐⭐⭐⭐ 难度4 → 12星星币
- ⭐⭐⭐⭐⭐ 难度5 → 18星星币

9种徽章：初出茅庐→小有成就→任务达人→坚持一周→...
