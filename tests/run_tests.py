"""零依赖测试运行器：python tests/run_tests.py

自动发现 tests/ 下 test_*.py 中的 test_* 函数并运行。
（也兼容 pytest：安装了 pytest 时可用 `pytest tests`。）
"""

from __future__ import annotations

import importlib.util
import inspect
import sys
import traceback
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent


def main() -> int:
    sys.path.insert(0, str(ROOT))
    passed = failed = errors = 0
    failures: list[tuple[str, str]] = []

    for test_file in sorted(HERE.glob("test_*.py")):
        module_name = f"tests.{test_file.stem}"
        spec = importlib.util.spec_from_file_location(module_name, test_file)
        module = importlib.util.module_from_spec(spec)
        try:
            spec.loader.exec_module(module)  # type: ignore[union-attr]
        except Exception:
            errors += 1
            failures.append((test_file.name, "导入失败:\n" + traceback.format_exc()))
            continue

        for name, fn in sorted(inspect.getmembers(module, inspect.isfunction)):
            if not name.startswith("test_"):
                continue
            try:
                fn()
                passed += 1
                print(f"  PASS  {test_file.name}::{name}")
            except AssertionError as e:
                failed += 1
                failures.append((f"{test_file.name}::{name}", f"断言失败: {e}"))
                print(f"  FAIL  {test_file.name}::{name}: {e}")
            except Exception:
                failed += 1
                failures.append((f"{test_file.name}::{name}", traceback.format_exc()))
                print(f"  FAIL  {test_file.name}::{name}: 异常")

    print(f"\n结果: {passed} 通过, {failed} 失败, {errors} 导入错误, 共 {passed + failed + errors}")
    for name, detail in failures:
        print(f"\n--- {name} ---\n{detail}")
    return 1 if (failed or errors) else 0


if __name__ == "__main__":
    raise SystemExit(main())
