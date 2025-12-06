# preserve.py —— 100% GitHub 数据源版（本地不放任何 CSV）
from neo4j import GraphDatabase
import json, requests, os, datetime, traceback
import tempfile

with open("config.json", encoding="utf-8") as f:
    config = json.load(f)

driver = GraphDatabase.driver(config["neo4j"]["uri"], auth=(config["neo4j"]["user"], config["neo4j"]["password"]))
FEISHU_URL = config["notify"]["webhook_url"]

# 改成你的 GitHub 仓库！
GITHUB_USER = "milu"
GITHUB_REPO = "xiyou-knowledge"
BRANCH = "main"

def send_feishu(title, content):
    payload = {"msg_type": "interactive",
               "card": {"header": {"title": {"tag": "plain_text", "content": title}, "template": "turquoise"},
                        "elements": [{"tag": "markdown", "content": content}]}}
    try: requests.post(FEISHU_URL, json=payload, timeout=10)
    except: pass

def download_csv(filename):
    url = f"https://raw.githubusercontent.com/{GITHUB_USER}/{GITHUB_REPO}/{BRANCH}/{filename}"
    r = requests.get(url)
    if r.status_code != 200:
        raise Exception(f"下载失败：{filename}")
    tmp = tempfile.NamedTemporaryFile(delete=False, mode="wb", suffix=".csv")
    tmp.write(r.content)
    tmp.close()
    return tmp.name

def preserve():
    try:
        with driver.session() as session:
            # 从 GitHub 下载最新 CSV
            person_path = download_csv("人物.csv")
            rel_path = download_csv("关系.csv")

            changes = []

            # 更新人物
            result = session.run(f'''
            LOAD CSV WITH HEADERS FROM "file:///{os.path.basename(person_path)}" AS row
            MERGE (p:person {{uid: row.uid}})
            WITH p, row, p.name AS old
            WHERE old <> row.姓名
            SET p.name = row.姓名, p.updated_at = datetime()
            RETURN row.uid, old, row.姓名 AS new
            ''')
            for r in result:
                changes.append(f"人物 · {r['row.uid']}：`{r['old']}` → **{r['new']}**")

            # 更新关系
            session.run(f'''
            LOAD CSV WITH HEADERS FROM "file:///{os.path.basename(rel_path)}" AS row
            MATCH (f:person {{uid: row.from_uid}}), (t:person {{uid: row.to_uid}})
            OPTIONAL MATCH (f)-[old:西游关系图 {{relation: row.relation}}]->(t) WHERE old.is_current = true
            SET old.is_current = false
            MERGE (f)-[r:西游关系图 {{relation: row.relation}}]->(t)
            ON CREATE SET r.is_current = true, r.中文称谓 = row.中文称谓
            ON MATCH  SET r.is_current = true, r.中文称谓 = row.中文称谓
            ''')

            if changes:
                send_feishu("知识已自动同步", f"检测到 GitHub 更新，共 {len(changes)} 处变更：\n" + "\n".join(changes[:15]))
            else:
                send_feishu("知识已同步", "GitHub 有更新，但无实质变更")

            # 清理临时文件
            os.unlink(person_path)
            os.unlink(rel_path)

    except Exception as e:
        send_feishu("保鲜失败", f"错误：\n```\n{traceback.format_exc()[-1000:]}\n```")

if __name__ == "__main__":
    preserve()
    send_feishu("保鲜完成", "最新图谱：http://localhost:7474")