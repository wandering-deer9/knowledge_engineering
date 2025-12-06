# preserve.py —— 100% GitHub 数据源版（本地不放任何 CSV） - 修复版
from neo4j import GraphDatabase
import time
import json, requests, os, datetime, traceback
import tempfile
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)  

with open("config.json", encoding="utf-8") as f:
    config = json.load(f)

driver = GraphDatabase.driver(config["neo4j"]["uri"], auth=(config["neo4j"]["user"], config["neo4j"]["password"]))
FEISHU_URL = config["notify"]["webhook_url"]

GITHUB_USER = "wandering-deer9"  
GITHUB_REPO = "knowledge_engineering"  
BRANCH = "main"  

def send_feishu(title, content):
    payload = {"msg_type": "interactive",
               "card": {"header": {"title": {"tag": "plain_text", "content": title}, "template": "turquoise"},
                        "elements": [{"tag": "markdown", "content": content}]}}
    try: requests.post(FEISHU_URL, json=payload, timeout=10)
    except: pass

def download_csv(filename):
    url = f"https://raw.githubusercontent.com/wandering-deer9/knowledge_engineering/main/import/{filename}"
    print(f"正在下载: {url}")
    
    for i in range(5):  
        try:

            r = requests.get(
                url, 
                verify=False,      
                timeout=30,        
                headers={'User-Agent': 'Mozilla/5.0'}  
            )
            if r.status_code == 200:
                tmp = tempfile.NamedTemporaryFile(delete=False, mode="wb", suffix=".csv")
                tmp.write(r.content)
                tmp.close()
                print(f"下载成功: {filename}")
                return tmp.name
            
            print(f"第 {i+1} 次尝试失败，状态码: {r.status_code}")
            
        except Exception as e:
            print(f"第 {i+1} 次连接失败: {str(e)}")
        
        if i < 4:
            print("3 秒后重试...")
            time.sleep(3)
    
    raise Exception(f"下载彻底失败：{filename}（多次尝试后仍无法连接）")

def preserve():
    try:
        with driver.session() as session:  
            person_path = download_csv("persons.csv")  
            rel_path = download_csv("relationships.csv") 

            changes = []

            
            result = session.run(f'''
            LOAD CSV WITH HEADERS FROM "file:///{os.path.basename(person_path)}" AS row
            MERGE (p:person {{uid: row.uid}})
            WITH p, row, p.name AS old
            WHERE old <> row.name  # 修复：用 row.name（英文列名）
            SET p.name = row.name, p.updated_at = datetime()
            RETURN row.uid, old, row.name AS new
            ''')
            for r in result:
                changes.append(f"人物 · {r['row.uid']}：`{r['old']}` → **{r['new']}**")


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


            os.unlink(person_path)
            os.unlink(rel_path)

    except Exception as e:
        send_feishu("保鲜失败", f"错误：\n```\n{traceback.format_exc()[-1000:]}\n```")

if __name__ == "__main__":
    preserve()
    send_feishu("保鲜完成", "最新图谱：http://localhost:7474/browser/")