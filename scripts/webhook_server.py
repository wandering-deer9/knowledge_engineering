# webhook_server.py —— 终极版：push 必触发保鲜
from flask import Flask, request
import subprocess
import os

app = Flask(__name__)

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.json
    if data and data.get("ref") == "refs/heads/main":  # 改成你的分支
        print("GitHub push 检测到！正在自动保鲜...")
        os.chdir(os.path.dirname(__file__))
        result = subprocess.run(["python", "preserve.py"], capture_output=True, text=True)
        print("保鲜脚本输出：")
        print(result.stdout)
        if result.stderr:
            print("错误：", result.stderr)
        return "保鲜已执行", 200
    return "忽略（非 main 分支）", 200

if __name__ == '__main__':
    print("Git 自动保鲜服务器已启动！等待 GitHub push...")
    app.run(host='0.0.0.0', port=5000)