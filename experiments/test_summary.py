"""
M2 摘要服务实验脚本

对比三种摘要模式的效果：
  1. 仅本地模型 (local)
  2. 仅大模型 API (llm)
  3. 混合模式 (hybrid)

使用 ROUGE 指标进行量化评估
"""

import requests
import json
import time

BASE_URL = "http://127.0.0.1:8002"

# ──────────────────────────────────────────────
# 测试数据：模拟会议记录 + 参考摘要
# ──────────────────────────────────────────────

TEST_CASES = [
    {
        "name": "产品需求讨论会",
        "text": """张总: 各位好，今天我们讨论一下新版本的产品需求。
李工: 好的，我先说一下技术方面的评估结果。上次提到的实时翻译功能，经过调研我们可以使用开源模型来实现。
王经理: 从市场角度来看，实时翻译是用户呼声最高的功能之一，建议优先开发。
张总: 那我们就确定把实时翻译作为下一版本的核心功能。李工你评估一下开发周期。
李工: 初步评估大概需要三周时间，包括模型集成、接口开发和测试。
王经理: 三周的话刚好赶上月底的发布窗口，我这边同步准备市场推广方案。
张总: 好的，那就这么定了。另外关于性能优化的问题，上个版本用户反馈加载速度有点慢。
李工: 这个我已经在排查了，主要是首次加载模型的时间比较长，我计划加一个预加载机制。
张总: 好，那李工你把实时翻译和性能优化都列入下一个迭代计划中。
王经理: 我补充一点，能不能加一个会议纪要的导出功能？很多客户都在问。
张总: 可以，这个排在翻译功能之后做。今天的会议就到这里，大家辛苦了。""",
        "reference": """本次会议讨论了新版本产品需求规划。会议确定将实时翻译功能作为下一版本核心功能，预计三周完成开发。同时需要解决首次加载模型速度慢的性能问题，计划加入预加载机制。会议纪要导出功能排在翻译功能之后开发。王经理将同步准备市场推广方案。"""
    },
    {
        "name": "项目进度周会",
        "text": """刘总: 今天开个项目进度周会，各组汇报一下本周进展。
赵工: 后端组这边，用户认证模块已经开发完成，正在进行接口联调。数据库迁移脚本也写好了。
孙经理: 前端组这周完成了首页改版和用户设置页面，还有两个页面在开发中。
刘总: 前端进度比预期慢了一点，原因是什么？
孙经理: 主要是设计稿改了两版，我们跟设计师沟通后现在已经确定了最终方案。
刘总: 好的，下周能追上进度吗？
孙经理: 可以的，这周末我们会加班赶一下。
赵工: 我这边有个问题需要确认，第三方支付接口的沙箱环境申请还没下来。
刘总: 这个我来催一下，预计什么时候能用？
赵工: 如果明天能批下来的话，周三就可以开始对接。
刘总: 好，我今天就去催。测试组有什么情况？
钱工: 测试组这周跑了150个用例，发现了8个bug，其中2个是严重级别的，已经提给赵工了。
赵工: 那两个严重bug我今天就修。
刘总: 好，那下周重点是：前端追进度、后端修bug对接支付、测试继续覆盖。散会。""",
        "reference": """本次项目进度周会各组汇报了本周进展。后端组完成用户认证模块开发和数据库迁移脚本；前端组完成首页改版和用户设置页面，因设计稿修改导致进度略慢，计划周末加班追进度。测试组执行了150个用例，发现8个bug（含2个严重）。待解决问题：第三方支付沙箱环境申请待批准，2个严重bug需当天修复。下周重点：前端追进度、后端修bug并对接支付、测试继续提升覆盖率。"""
    },
    {
        "name": "技术架构评审会",
        "text": """陈总: 今天我们评审一下微服务改造的技术方案。
周工: 我来介绍一下整体方案。目前我们的单体应用拆分为五个微服务：用户服务、订单服务、支付服务、通知服务和网关服务。
吴工: 服务间通信用什么方案？
周工: 同步调用用 gRPC，异步消息用 RabbitMQ。
吴工: gRPC 的话需要注意服务发现的问题，建议用 Consul。
陈总: 数据库怎么拆？
周工: 每个服务独立数据库，用户服务用 PostgreSQL，订单服务用 MySQL，通知服务用 MongoDB。
吴工: 我有个担忧，跨服务事务怎么保证一致性？
周工: 我们采用 Saga 模式，通过事件驱动来保证最终一致性。
陈总: 这个方案的风险点在哪里？
周工: 主要风险是迁移过程中的数据一致性，和服务拆分粒度是否合适。
陈总: 建议先做一个试点，选一个风险最低的服务先迁移。
周工: 可以，我建议先迁移通知服务，它依赖最少。
陈总: 好的，那就确定先迁移通知服务作为试点，两周后看效果再决定下一步。""",
        "reference": """本次技术架构评审会讨论了单体应用微服务改造方案。方案将应用拆分为用户、订单、支付、通知、网关五个微服务，同步通信使用gRPC，异步通信使用RabbitMQ，服务发现建议用Consul。数据库按服务独立拆分。跨服务事务采用Saga模式保证最终一致性。主要风险是迁移数据一致性和拆分粒度问题。决策：先以通知服务为试点进行微服务迁移，两周后评估效果再推进。"""
    },
]


def call_summary_api(endpoint: str, text: str, session_id: str = "test") -> dict:
    """调用摘要 API"""
    try:
        resp = requests.post(
            f"{BASE_URL}{endpoint}",
            json={"session_id": session_id, "text": text},
            timeout=60,
        )
        return resp.json()
    except Exception as e:
        return {"status": "error", "summary": f"请求失败: {e}"}


def call_evaluate_api(reference: str, hypothesis: str) -> dict:
    """调用 ROUGE 评估 API"""
    try:
        resp = requests.post(
            f"{BASE_URL}/api/v1/summary/evaluate",
            json={"reference": reference, "hypothesis": hypothesis},
            timeout=30,
        )
        return resp.json()
    except Exception as e:
        return {"status": "error", "message": f"评估请求失败: {e}"}


def run_experiment():
    """运行对比实验"""
    print("=" * 80)
    print("M2 摘要服务对比实验")
    print("=" * 80)

    # 先检查服务是否可用
    try:
        health = requests.get(f"{BASE_URL}/health", timeout=5).json()
        print(f"\n服务状态: {health}")
        print(f"本地模型: {'已加载' if health.get('local_model_loaded') else '未加载（将跳过 local 模式）'}")
    except Exception:
        print("\n[错误] M2 摘要服务未启动，请先运行: python services/summary_server.py")
        return

    endpoints = {
        "local": "/api/v1/summary/generate_local",
        "llm": "/api/v1/summary/generate_llm",
        "hybrid": "/api/v1/summary/generate",
    }

    all_results = []

    for case in TEST_CASES:
        print(f"\n{'─' * 60}")
        print(f"测试用例: {case['name']}")
        print(f"{'─' * 60}")

        case_results = {"name": case["name"]}

        for mode, endpoint in endpoints.items():
            print(f"\n  [{mode.upper()}] 正在生成摘要...")
            start_time = time.time()

            result = call_summary_api(endpoint, case["text"])
            elapsed = time.time() - start_time

            summary = result.get("summary", "")
            status = result.get("status", "error")

            print(f"  状态: {status} | 耗时: {elapsed:.2f}s")

            if status == "success" and summary:
                # 截断显示
                display = summary[:150] + "..." if len(summary) > 150 else summary
                print(f"  摘要: {display}")

                # 计算 ROUGE
                eval_result = call_evaluate_api(case["reference"], summary)
                if eval_result.get("status") == "success":
                    r1 = eval_result["rouge_1"]["f"]
                    r2 = eval_result["rouge_2"]["f"]
                    rl = eval_result["rouge_l"]["f"]
                    print(f"  ROUGE-1: {r1:.4f} | ROUGE-2: {r2:.4f} | ROUGE-L: {rl:.4f}")
                    case_results[mode] = {
                        "rouge_1": r1, "rouge_2": r2, "rouge_l": rl,
                        "time": elapsed
                    }
                else:
                    print(f"  评估失败: {eval_result.get('message', '未知错误')}")
                    case_results[mode] = {"error": "评估失败", "time": elapsed}
            else:
                print(f"  摘要失败: {summary[:100] if summary else '无输出'}")
                case_results[mode] = {"error": summary or "无输出", "time": elapsed}

        all_results.append(case_results)

    # 输出汇总表格
    print(f"\n\n{'=' * 80}")
    print("实验结果汇总")
    print(f"{'=' * 80}")
    print(f"{'测试用例':<20} {'模式':<10} {'ROUGE-1':<10} {'ROUGE-2':<10} {'ROUGE-L':<10} {'耗时(s)':<10}")
    print("-" * 70)

    for case_result in all_results:
        for mode in ["local", "llm", "hybrid"]:
            r = case_result.get(mode, {})
            if "error" in r:
                print(f"{case_result['name']:<20} {mode:<10} {'N/A':<10} {'N/A':<10} {'N/A':<10} {r.get('time', 0):<10.2f}")
            else:
                print(f"{case_result['name']:<20} {mode:<10} {r.get('rouge_1', 0):<10.4f} {r.get('rouge_2', 0):<10.4f} {r.get('rouge_l', 0):<10.4f} {r.get('time', 0):<10.2f}")

    print(f"\n实验完成！共测试 {len(TEST_CASES)} 个用例 x 3 种模式")


if __name__ == "__main__":
    run_experiment()
