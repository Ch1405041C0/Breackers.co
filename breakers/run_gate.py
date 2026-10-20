"""CLI entry point for BREAKERS Playwright Quality Gate."""
import argparse
import json

from breakers.playwright_gate import gate_exit_code, run_playwright_gate


def main() -> int:
    parser = argparse.ArgumentParser(description="BREAKERS deployment quality gate")
    parser.add_argument("target_url")
    parser.add_argument("--suite", default="tests/playwright")
    parser.add_argument("--browser", default="chromium")
    args = parser.parse_args()

    result = run_playwright_gate(args.target_url, args.suite, browser=args.browser)
    print(json.dumps(result.to_dict(), indent=2))
    print("BREAKERS DECISION: GO" if not result.blocking else "BREAKERS DECISION: NO-GO")
    return gate_exit_code(result)


if __name__ == "__main__":
    raise SystemExit(main())
