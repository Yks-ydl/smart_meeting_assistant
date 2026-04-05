import subprocess
import time
import sys
import os

def start_services():
    print(" 正在启动智能会议助手微服务集群...")
    
    # 设置 Hugging Face 国内镜像源，解决模型下载超时问题
    os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"
    # 解决 Windows 环境下常见的 OMP 冲突报错 (OMP: Error #15)
    os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
    print("已设置环境变量 HF_ENDPOINT 和 KMP_DUPLICATE_LIB_OK")
    
    # 定义需要启动的服务列表
    services = [
        {"name": "M1 - ASR Service", "script": "services/asr_server.py", "port": 8001},
        {"name": "M2 - Summary Service", "script": "services/summary_server.py", "port": 8002},
        {"name": "M3 - Translation & Action", "script": "services/translation_server.py", "port": 8003},
        {"name": "M4 - Sentiment Analysis", "script": "services/sentiment_server.py", "port": 8004},
        {"name": "M5 - Main Gateway", "script": "gateway/main_server.py", "port": 8000},
        {"name": "M6 - Audio Input", "script": "services/audio_input_server.py", "port": 8005},
    ]

    processes = []
    
    for svc in services:
        print(f"启动 {svc['name']} (Port: {svc['port']})...")
        # 使用 sys.executable 确保使用当前的 python 环境
        p = subprocess.Popen([sys.executable, svc["script"]])
        processes.append(p)
        time.sleep(1) # 稍微延迟，避免输出混乱
        
    print("\n 所有服务已启动！")
    print("您可以通过 Gateway 访问 WebSocket 测试，或者直接访问各微服务的 Swagger 文档：")
    for svc in services:
        print(f" - {svc['name']}: http://127.0.0.1:{svc['port']}/docs")
        
    print("\n按 Ctrl+C 停止所有服务...")
    
    try:
        # 保持主进程运行
        for p in processes:
            p.wait()
    except KeyboardInterrupt:
        print("\n正在停止所有服务...")
        for p in processes:
            p.terminate()
        print("所有服务已安全停止。")

if __name__ == "__main__":
    start_all_script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(start_all_script_dir)
    start_services()
