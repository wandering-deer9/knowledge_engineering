# webhook_server.py —— GitHub 一 push 就自动保鲜
from flask import Flask, request, jsonify
import subprocess
import os

app = Flask(__name__)

@app.route('/webhook', methods=['POST'])
def webhook():
    # 简单验证（生产建议加 secret）
    try:
        # 直接触发保鲜脚本
        os.chdir(os.path.dirname(__file__))  # 切到 scripts 目录
        result = subprocess.run(
            ["python", "preserve.py"],
            capture_output=True, text=True, timeout=30
        )
        if result.returncode == 0:
            return jsonify({"status": "保鲜成功", "output": result.stdout}), 200
        else:
            return jsonify({"status": "保鲜失败", "error": result.stderr}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    print("Git 自动保鲜服务器已启动：http://localhost:5000")
    app.run(host='0.0.0.0', port=5000)