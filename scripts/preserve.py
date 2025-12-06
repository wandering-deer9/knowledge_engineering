import os
import uuid
import time
import json
import requests
import traceback
import urllib3
from neo4j import GraphDatabase

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

with open("config.json", encoding="utf-8") as f:
    config = json.load(f)

driver = GraphDatabase.driver(
    config["neo4j"]["uri"],
    auth=(config["neo4j"]["user"], config["neo4j"]["password"])
)
FEISHU_URL = config["notify"]["webhook_url"]

GITHUB_USER = "wandering-deer9"
GITHUB_REPO = "knowledge_engineering"
BRANCH = "main"
NEO4J_IMPORT_DIR = r"E:\zijie\neo4j-community-2025.10.1\import"
os.makedirs(NEO4J_IMPORT_DIR, exist_ok=True)

def send_feishu(title, content):
    payload = {
        "msg_type": "interactive",
        "card": {
            "header": {"title": {"tag": "plain_text", "content": title}, "template": "turquoise"},
            "elements": [{"tag": "markdown", "content": content}]
        }
    }
    try:
        requests.post(FEISHU_URL, json=payload, timeout=10)
    except:
        pass

def download_csv(filename):
    url = f"https://ghproxy.net/https://raw.githubusercontent.com/{GITHUB_USER}/{GITHUB_REPO}/{BRANCH}/import/{filename}"
    print(f"正在下载: {url}")

    for i in range(3):
        try:
            r = requests.get(url, verify=False, timeout=30, headers={'User-Agent': 'Mozilla/5.0'})
            if r.status_code == 200:
                final_path = os.path.join(NEO4J_IMPORT_DIR, f"github_{filename}_{uuid.uuid4().hex[:8]}.csv")
                with open(final_path, "wb") as f:
                    f.write(r.content)
                print(f"下载成功 → {final_path}")
                return final_path
        except Exception as e:
            print(f"第 {i+1} 次失败: {e}")
        if i < 2:
            time.sleep(3)
    raise Exception(f"下载失败：{filename}")

def preserve():
    changes = []
    person_path = None
    rel_path = None

    try:
        with driver.session() as session:
            person_path = download_csv("persons.csv")
            rel_path = download_csv("relationships.csv")

            result = session.run(f'''
            LOAD CSV WITH HEADERS FROM "file:///{os.path.basename(person_path)}" AS row
            MERGE (p:person {{uid: row.uid}})
            WITH p, row, p.name AS old
            WHERE old <> row.name
            SET p.name = row.name, p.updated_at = datetime()
            RETURN row.uid AS uid, old AS old_name, row.name AS new_name
            ''')
            for r in result:
                changes.append(f"人物 · {r['uid']}：`{r['old_name']}` → **{r['new_name']}**")

            rel_result = session.run(f'''
            LOAD CSV WITH HEADERS FROM "file:///{os.path.basename(rel_path)}" AS row
            MATCH (f:person {{uid: row.from_uid}}), (t:person {{uid: row.to_uid}})
            OPTIONAL MATCH (f)-[old:西游关系图 {{relation: row.relation}}]->(t)
              WHERE old.is_current = true AND coalesce(old.中文称谓, '') <> row.中文称谓
            WITH f, t, row, old
            SET old.is_current = false, old.valid_to = datetime()
            MERGE (f)-[r:西游关系图 {{relation: row.relation}}]->(t)
            ON CREATE SET r.is_current = true, r.valid_from = datetime(), r.中文称谓 = row.中文称谓
            ON MATCH  SET r.is_current = true, r.valid_from = datetime(), r.中文称谓 = row.中文称谓
            RETURN
              row.from_uid AS f,
              row.to_uid AS t,
              row.relation AS rel,
              coalesce(old.中文称谓, '<无>') AS old_label,
              row.中文称谓 AS new_label,
              CASE WHEN old IS NULL THEN '新增关系' ELSE '称谓变更' END AS type
            ''')

            for r in rel_result:
                if r['type'] == '新增关系':
                    changes.append(f"关系 · 新增：{r['f']} —[{r['rel']}]→ {r['t']} （称谓：{r['new_label']}）")
                else:
                    changes.append(f"关系 · 修改：{r['f']} —[{r['rel']}]→ {r['t']} 称谓 `{r['old_label']}` → **{r['new_label']}**")

            if changes:
                send_feishu("知识已自动同步", f"检测到 GitHub 更新，共 {len(changes)} 处变更：\n" + "\n".join(changes[:30]))
            else:
                send_feishu("知识已同步", "GitHub 有更新，但无实质变更")

    except Exception as e:
        send_feishu("保鲜失败", f"错误：\n```\n{traceback.format_exc()[-1200:]}\n```")
    finally:
        for p in [person_path, rel_path]:
            if p and os.path.exists(p):
                try:
                    os.unlink(p)
                except:
                    pass

if __name__ == "__main__":
    preserve()
    send_feishu("保鲜完成", "最新图谱：http://localhost:7474/browser/")