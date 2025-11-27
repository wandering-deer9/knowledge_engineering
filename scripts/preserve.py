# preserve.py —— 终极精准明细版：人物+关系变更一条一条全报出来！
from neo4j import GraphDatabase
import json, os, datetime, requests, glob, traceback, urllib.parse, hashlib, shutil

with open("config.json", encoding="utf-8") as f:
    config = json.load(f)

driver = GraphDatabase.driver(config["neo4j"]["uri"], auth=(config["neo4j"]["user"], config["neo4j"]["password"]))
FEISHU_URL = config["notify"]["webhook_url"]
IMPORT_DIR = r"E:\zijie\neo4j-community-2025.10.1\import"
ARCHIVE_DIR = os.path.join(IMPORT_DIR, "已处理")
os.makedirs(ARCHIVE_DIR, exist_ok=True)

def send_feishu(title, content):
    payload = {"msg_type": "interactive",
               "card": {"header": {"title": {"tag": "plain_text", "content": title}, "template": "red"},
                        "elements": [{"tag": "markdown", "content": content}]}}
    try: requests.post(FEISHU_URL, json=payload, timeout=10)
    except: pass

def safe_filename(f): return f"file:///{urllib.parse.quote(os.path.basename(f), safe='')}"

def get_current_file_hash():
    files = [f for f in glob.glob(os.path.join(IMPORT_DIR, "*人物*.csv")) + 
                   glob.glob(os.path.join(IMPORT_DIR, "*关系*.csv")) if "已处理" not in f]
    if not files: return "empty"
    h = hashlib.md5()
    for f in sorted(files):
        with open(f, "rb") as fp:
            h.update(fp.read())
        h.update(str(os.path.getmtime(f)).encode())
    return h.hexdigest()

def preserve():
    person_files = [f for f in glob.glob(os.path.join(IMPORT_DIR, "*人物*.csv")) if "已处理" not in f]
    rel_files    = [f for f in glob.glob(os.path.join(IMPORT_DIR, "*关系*.csv")) if "已处理" not in f]
    all_files = person_files + rel_files
    
    if not all_files:
        return

    current_hash = get_current_file_hash()

    try:
        with driver.session() as session:
            last = session.run("MATCH (h:FileHashTracker) RETURN h.hash AS h").single()
            last_hash = last["h"] if last else None
            if current_hash == last_hash:
                return

            change_lines = []   # 存所有变更明细

            # 1. 人物变更（精准）
            for pf in person_files:
                result = session.run(f'''
                LOAD CSV WITH HEADERS FROM "{safe_filename(pf)}" AS row
                MATCH (p:person {{uid: row.uid}})
                WITH p, row, p.name AS old_name
                WHERE old_name <> row.姓名
                SET p.name = row.姓名, p.is_current = true, p.valid_from = datetime()
                RETURN row.uid AS uid, old_name, row.姓名 AS new_name
                ''')
                for r in result:
                    change_lines.append(f"人物 · {r['uid']}：`{r['old_name']}` → **{r['new_name']}**")

            # 2. 关系变更（终极精准！每条新增/失效都报出来）
            for rf in rel_files:
                result = session.run(f'''
                LOAD CSV WITH HEADERS FROM "{safe_filename(rf)}" AS row
                MATCH (f:person {{uid: row.from_uid}}), (t:person {{uid: row.to_uid}})
                
                // 情况1：原来有这条关系，但称谓变了
                OPTIONAL MATCH (f)-[old:西游关系图 {{relation: row.relation}}]->(t)
                  WHERE old.is_current = true AND coalesce(old.中文称谓, '') <> row.中文称谓
                WITH f, t, row, old
                SET old.is_current = false, old.valid_to = datetime()
                
                // 情况2：原来没有这条关系 → 新增
                MERGE (f)-[r:西游关系图 {{relation: row.relation}}]->(t)
                ON CREATE SET r.is_current = true, r.valid_from = datetime(), r.中文称谓 = row.中文称谓
                ON MATCH  SET r.is_current = true, r.valid_from = datetime(), r.中文称谓 = row.中文称谓
                
                // 返回明细
                WITH row, old
                RETURN 
                  row.from_uid AS from_uid,
                  row.to_uid AS to_uid,
                  row.relation AS rel_type,
                  coalesce(old.中文称谓, '<无>') AS old_label,
                  row.中文称谓 AS new_label,
                  CASE WHEN old IS NOT NULL THEN '称谓变更' ELSE '新增关系' END AS change_type
                ''')
                
                for r in result:
                    if r['change_type'] == '新增关系':
                        change_lines.append(f"关系 · 新增：{r['from_uid']} —[{r['rel_type']}]→ {r['to_uid']} （称谓：{r['new_label']}）")
                    else:
                        change_lines.append(f"关系 · 修改：{r['from_uid']} —[{r['rel_type']}]→ {r['to_uid']} 称谓 `{r['old_label']}` → **{r['new_label']}**")

            # 3. 发飞书（精准明细）
            if change_lines:
                lines = [f"知识已自动更新（{len(all_files)} 个文件，共 {len(change_lines)} 处变更）"] + change_lines
                send_feishu("知识保鲜成功", "\n".join(lines))
            else:
                send_feishu("知识已更新", f"检测到 {len(all_files)} 个文件变更，但无实质内容变化")

            # 4. 归档
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            for f in all_files:
                shutil.move(f, os.path.join(ARCHIVE_DIR, f"{timestamp}_{os.path.basename(f)}"))

            # 5. 更新哈希
            session.run("MERGE (h:FileHashTracker) SET h.hash = $hash", hash=current_hash)

    except Exception as e:
        send_feishu("保鲜崩溃", f"文件未归档！\n```\n{traceback.format_exc()[-1800:]}\n```")

if __name__ == "__main__":
    preserve()