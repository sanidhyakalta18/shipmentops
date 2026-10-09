"""Run basic ShipmentOps agent evaluations and save a report."""

import json
import time
from datetime import datetime, timezone
from pathlib import Path

from react_agent.graph import graph

CASES = [
    {
        "name": "Delivered shipment",
        "question": "What is the status of SHP1001?",
        "shipment_id": "SHP1001",
        "expected_groups": [["delivered"]],
    },
    {
        "name": "Delivery exception",
        "question": "Why is SHP1002 delayed?",
        "shipment_id": "SHP1002",
        "expected_groups": [["incomplete address"]],
    },
    {
        "name": "Recommended next action",
        "question": "What should support do next for SHP1002?",
        "shipment_id": "SHP1002",
        "expected_groups": [
            ["address"],
            ["confirm", "verify"],
            ["reattempt", "re-attempt", "retry", "another delivery"],
        ],
    },
    {
        "name": "Unknown shipment",
        "question": "Where is SHP9999?",
        "shipment_id": "SHP9999",
        "expected_groups": [
            ["not found", "no matching", "no record", "could not find",
             "couldn't find", "cannot find", "does not exist"],
        ],
    },
    {
        "name": "Lowercase shipment ID",
        "question": "Please check shipment shp1002.",
        "shipment_id": "SHP1002",
        "expected_groups": [["incomplete address"]],
    },
]


def extract_text(content):
    if isinstance(content, str):
        return content

    if isinstance(content, list):
        return "\n".join(
            block if isinstance(block, str) else block.get("text", "")
            for block in content
            if isinstance(block, (str, dict))
        )

    return ""


def run_evaluations():
    results = []

    for case in CASES:
        started = time.perf_counter()

        try:
            # Each case starts with a fresh conversation.
            output = graph.invoke(
                {"messages": [("user", case["question"])]},
                config={"recursion_limit": 12},
            )

            messages = output["messages"]
            answer = extract_text(messages[-1].content)
            answer_lower = answer.lower()

            tool_calls = [
                call
                for message in messages
                for call in getattr(message, "tool_calls", [])
            ]

            correct_lookup = any(
                call.get("name") == "get_shipment"
                and str(
                    call.get("args", {}).get("shipment_id", "")
                ).strip().upper() == case["shipment_id"]
                for call in tool_calls
            )

            content_check = all(
                any(phrase in answer_lower for phrase in group)
                for group in case["expected_groups"]
            )

            result = {
                "name": case["name"],
                "question": case["question"],
                "passed": correct_lookup and content_check,
                "correct_tool_lookup": correct_lookup,
                "content_check": content_check,
                "answer": answer,
                "tool_calls": tool_calls,
                "error": None,
            }

        except Exception as error:
            # Avoid copying potentially sensitive exception details.
            result = {
                "name": case["name"],
                "question": case["question"],
                "passed": False,
                "error": type(error).__name__,
            }

        result["latency_seconds"] = round(
            time.perf_counter() - started, 2
        )
        results.append(result)

        label = "PASS" if result["passed"] else "FAIL"
        print(f"{label}: {case['name']}", flush=True)

    passed = sum(result["passed"] for result in results)
    errors = sum(result["error"] is not None for result in results)

    report = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "evaluation_type": "Basic tool-use and keyword regression checks",
        "limitations": (
            "Five synthetic cases; keyword checks can miss semantic "
            "errors or reject valid paraphrases. Review answers manually. "
            "This does not measure overall factual accuracy."
        ),
        "total_cases": len(results),
        "passed": passed,
        "api_or_runtime_errors": errors,
        "results": results,
    }

    report_path = Path(__file__).resolve().parent / "evaluation_report.json"
    report_path.write_text(
        json.dumps(report, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print(f"\nPassed: {passed}/{len(results)}")
    print(f"API/runtime errors: {errors}")
    print(f"Report saved: {report_path.name}")


if __name__ == "__main__":
    run_evaluations()