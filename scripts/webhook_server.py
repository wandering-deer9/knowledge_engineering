# webhook_server.py —— 收到 GitHub push 就自动保鲜
from flask import Flask, request
import subprocess
import os

app = Flask(__name__)

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.json
    if data and data.get("ref") == "refs/heads/main":  # 改成你的分支
        print("GitHub push 检测到！正在自动同步最新数据...")
        os.chdir(os.path.dirname(__file__))
        subprocess.run(["python", "preserve.py"])
        return "保鲜已触发", 200
    return "忽略", 200

if __name__ == '__main__':
    print("Git 自动保鲜服务器已启动！等待 push...")
    app.run(host='0.0.0.0', port=5000)