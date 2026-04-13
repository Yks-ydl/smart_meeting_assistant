import subprocess
import time
import sys
import os

from gateway.demo_source import use_vcsum_demo_source


def terminate_processes(processes):
    for proc in processes:
        if proc.poll() is None:
            proc.terminate()


def build_service_catalog() -> list[dict]:
    # Keep startup selection data-driven so the default audio path does not require M7.
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

    if use_vcsum_demo_source():
        print("检测到 MEETING_DEMO_SOURCE=vcsum，保留 M7 数据服务启动。")
        return services

    print("未检测到 MEETING_DEMO_SOURCE=vcsum，默认走目录音频 demo，跳过 M7 数据服务启动。")
    return [svc for svc in services if svc["script"] != "services/data_server.py"]


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
