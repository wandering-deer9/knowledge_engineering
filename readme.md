# 动态知识图谱自动同步系统

基于 GitHub + Neo4j + 飞书机器人的全自动知识图谱保鲜系统。  
只要在 GitHub 仓库中修改人物或关系 CSV 并执行 `git push`，系统即可在 10 秒内完成图谱更新并通过飞书推送详细变更记录。

## 系统特性

- 完全 Git 驱动：CSV 文件即数据源，无需手动导入
- 精准变更感知：人物名称变更、关系新增、关系称谓变更均逐条上报
- 无人值守：Webhook + ngrok 实现全自动触发
- 飞书实时通知：支持多达 30 条变更明细展示
- 国内网络友好：内置 ghproxy 加速 + 重试机制，稳定可靠
- 历史可追溯：旧关系自动标记 `is_current = false` 并记录 `valid_to` 时间

## 架构总览
GitHub Repository
└── import/
    ├── persons.csv
    └── relationships.csv
↓ git push
Webhook → ngrok → webhook_server.py (Flask)
↓
preserve.py

从 GitHub 下载最新 CSV
保存至 Neo4j import 目录
执行 Cypher 更新图谱
收集变更明细 → 飞书推送

text## 环境要求

| 组件               | 版本要求                          |
|--------------------|-----------------------------------|
| Neo4j Community    | 5.x（推荐 2025.10.1）             |
| Python             | 3.9+                              |
| Git                | 任意版本                          |
| ngrok              | 免费账户即可                      |

## 快速部署

### 1. 克隆仓库并放置文件

将本仓库克隆至本地任意目录，例如：
E:\zijie\knowledge_engineering
text目录结构保持如下：
knowledge_engineering/
├── import/                     ← 存放 CSV（可为空，系统会从 GitHub 拉取）
├── scripts/
│   ├── config.json
│   ├── preserve.py
│   └── webhook_server.py
├── ngrok.exe
└── 一键启动保鲜系统.bat
### 2. 修改配置文件（共 4 处）

| 文件                     | 需要修改的内容                        | 示例/说明                                  |
|--------------------------|---------------------------------------|--------------------------------------------|
| `scripts/config.json`    | `webhook_url`                         | 飞书自定义机器人的 Webhook 地址           |
| `scripts/preserve.py`    | `NEO4J_IMPORT_DIR`                    | Neo4j 的 import 目录（绝对路径）           |
| `scripts/preserve.py`    | `GITHUB_USER`                         | 你的 GitHub 用户名                         |
| `scripts/preserve.py`    | `GITHUB_REPO`                         | 你的仓库名称                               |

### 3. 启动系统

双击项目根目录下的 `一键启动保鲜系统.bat`，将依次启动：

1. Neo4j 服务
2. Webhook 监听服务（5000 端口）
3. ngrok 公网隧道

### 4. 配置 GitHub Webhook

1. 进入仓库 → Settings → Webhooks → Add webhook
2. Payload URL：`https://<你的ngrok域名>.ngrok-free.app/webhook`
3. Content type：`application/json`
4. Events：选择 **Just the push event**
5. 点击 **Add webhook**

## CSV 文件规范

### import/persons.csv

```csv
uid,name
孙悟空,斗战胜佛
唐僧,玄奘法师
猪八戒,猪悟能
import/relationships.csv
csvfrom_uid,to_uid,relation,中文称谓
孙悟空,唐僧,apprentice,大师兄
猪八戒,唐僧,apprentice,二师兄
孙悟空,如来佛祖,eternal_enemy,五指山下死对头

uid/from_uid/to_uid 必须唯一且保持一致
中文称谓 字段支持任意描述文字

##变更上报规则

变更类型是否上报说明人物名称变更是精确显示旧→新名称新增人物是MERGE 时首次创建触发新增关系是无同类型关系时触发关系称谓变更是同类型关系存在但称谓不同时触发仅修改空格/换行否视为“无实质变更”
常见问题
