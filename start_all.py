import subprocess
import time
import sys
import os


def terminate_processes(processes):
    for proc in processes:
        if proc.poll() is None:
            proc.terminate()


def build_service_catalog() -> list[dict]:
    # Keep service definition centralized so mode-based filtering does not duplicate service metadata.
    services = [
        {"name": "M1 - ASR Service", "script": "services/asr_server.py", "port": 8001},
        {
            "name": "M2 - Summary Service",
            "script": "services/summary_server.py",
            "port": 8002,
        },
        {
            "name": "M3 - Translation & Action",
            "script": "services/translation_server.py",
            "port": 8003,
        },
        {
            "name": "M4 - Sentiment Analysis",
            "script": "services/sentiment_server.py",
            "port": 8004,
        },
        {"name": "M5 - Main Gateway", "script": "gateway/main_server.py", "port": 8000},
        {
            "name": "M6 - Audio Input",
            "script": "services/audio_input_server.py",
            "port": 8005,
        },
        {
            "name": "M7 - Data Service (VCSum)",
            "script": "services/data_server.py",
            "port": 8006,
        },
    ]

    summary_mode = os.getenv("SUMMARY_EXECUTION_MODE", "local").strip().lower()
    if summary_mode == "remote":
        print("检测到 SUMMARY_EXECUTION_MODE=remote，跳过本地 M2 摘要服务启动。")
        print(f"当前远端摘要地址: {os.getenv('SUMMARY_SERVICE_URL', '')}")
        services = [svc for svc in services if svc["script"] != "services/summary_server.py"]

    return services


def start_services():
    print(" 正在启动智能会议助手微服务集群...")

    # 设置 Hugging Face 国内镜像源，解决模型下载超时问题
    os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"
    # 解决 Windows 环境下常见的 OMP 冲突报错 (OMP: Error #15)
    os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
    print("已设置环境变量 HF_ENDPOINT 和 KMP_DUPLICATE_LIB_OK")

    services = build_service_catalog()

    processes = []
    failed_services = []

    for svc in services:
        print(f"启动 {svc['name']} (Port: {svc['port']})...")
        # 使用 sys.executable 确保使用当前的 python 环境
        p = subprocess.Popen([sys.executable, svc["script"]])
        processes.append(p)
        time.sleep(1)  # 稍微延迟，避免输出混乱

        exit_code = p.poll()
        if exit_code is not None:
            failed_services.append(
                {
                    "name": svc["name"],
                    "port": svc["port"],
                    "exit_code": exit_code,
                }
            )

    if failed_services:
        print("\n 以下服务启动失败：")
        for svc in failed_services:
            print(
                f" - {svc['name']} (Port: {svc['port']})，退出码: {svc['exit_code']}"
            )
        terminate_processes(processes)
        return 1

    print("\n 所有服务已启动！")
    print(
        "您可以通过 Gateway 访问 WebSocket 测试，或者直接访问各微服务的 Swagger 文档："
    )
    for svc in services:
        print(f" - {svc['name']}: http://127.0.0.1:{svc['port']}/docs")

    print("\n按 Ctrl+C 停止所有服务...")

    try:
        # 持续监控子进程，一旦有服务异常退出则停止全部服务。
        while True:
            for idx, p in enumerate(processes):
                exit_code = p.poll()
                if exit_code is not None:
                    svc = services[idx]
                    print(
                        f"\n {svc['name']} (Port: {svc['port']}) 异常退出，退出码: {exit_code}"
                    )
                    terminate_processes(processes)
                    return 1
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n正在停止所有服务...")
        terminate_processes(processes)
        print("所有服务已安全停止。")
        return 0


if __name__ == "__main__":
    start_all_script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(start_all_script_dir)
    sys.exit(start_services())
