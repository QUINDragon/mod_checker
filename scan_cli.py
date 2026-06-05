"""
星露谷物语 MOD 检查工具 - 命令行入口
用法:
    python scan_cli.py                  # 交互模式（默认）
    python scan_cli.py --quick          # 仅快筛
    python scan_cli.py --deep "MOD名"   # 深度分析指定MOD
    python scan_cli.py --quick --export json  # 快筛并导出JSON
    python scan_cli.py --refresh        # 刷新N网缓存后进入交互模式
    python scan_cli.py --no-watch       # 禁用文件监听
"""
import argparse, json, sys, os

from quick_scan import quick_scan
from deep_scan import deep_scan_multiple
from cli_utils import green, red, yellow, bold, cyan, Colors, fuzzy_match
try:
    from file_watcher import start_watching, stop_watching, is_watching
except ImportError:
    def start_watching(): pass
    def stop_watching(): pass
    def is_watching(): return False


def _print_report(report: dict) -> None:
    """打印单个深度分析报告"""
    print("=" * 50)
    print(f"深度分析: {report['name']} v{report['version']}")
    print("=" * 50)

    qs = report.get("quick_status", {})
    print(f"快筛状态: {qs.get('status_text', '未知')}")
    if qs.get("updated_time"):
        print(f"最后更新: {qs['updated_time'][:10]}")

    ss = report.get("smapi_status", {})
    print(f"SMAPI状态: {ss.get('status_text', '未知')}")
    if ss.get("detail"):
        print(f"  详情: {ss['detail']}")

    deps = report.get("dependencies", {})
    missing = deps.get("missing", [])
    if missing:
        print(f"缺失依赖 ({len(missing)}):")
        for d in missing:
            print(f"  ❌ {d}")
    else:
        print("依赖检查: ✅ 完整")

    conflicts = report.get("conflicts", [])
    if conflicts:
        print(f"CP包冲突 ({len(conflicts)}):")
        for c in conflicts[:5]:
            print(f"  ⚠️ {c}")
    else:
        print("CP包冲突: ✅ 无冲突")

    map_conflicts = report.get("map_conflicts", [])
    if map_conflicts:
        print(f"地图文件冲突 ({len(map_conflicts)}):")
        for mc in map_conflicts[:5]:
            mods = ", ".join(mc.get("conflicting_mods", []))
            print(f"  🗺️ {mc['file']} ← 与 {mods} 冲突")
    else:
        print("地图冲突: ✅ 无冲突")

    recs = report.get("recommendations", [])
    if recs:
        print("建议:")
        for rec in recs:
            print(f"  💡 {rec}")
    print()


def _export_json(reports: list, path: str = "-") -> None:
    """导出深度分析报告为 JSON"""
    if path == "-":
        print(json.dumps(reports, ensure_ascii=False, indent=2))
    else:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(reports, f, ensure_ascii=False, indent=2)
        print(f"结果已导出到: {path}")


def cmd_quick(export: str = "") -> None:
    """快筛模式"""
    print("星露谷物语 MOD 快筛")
    print("=" * 50)
    results = quick_scan()
    if not results:
        print("没有找到任何MOD")
        return

    print(f"\n共 {len(results)} 个MOD")
    ok = sum(1 for r in results if r["status"] == "ok")
    warn = sum(1 for r in results if r["status"] == "warning")
    risk = sum(1 for r in results if r["status"] == "risk")
    print(f"统计: ✅ {ok} | ⚠️ {warn} | 🔴 {risk}")

    if export == "json":
        out = [{"name": r["name"], "version": r["version"], "status": r["status_text"],
                 "mod_type": r["mod_type"]} for r in results]
        print("\n" + json.dumps(out, ensure_ascii=False, indent=2))


def cmd_deep(mod_name: str, export: str = "") -> None:
    """深度分析单个 MOD（支持模糊匹配）"""
    from scanner import scan_mods
    mods = scan_mods()
    names = [m["name"] for m in mods]

    # 尝试精确匹配
    exact = [m for m in mods if m["name"].lower() == mod_name.lower()]
    if exact:
        matched = exact[0]["name"]
    else:
        # 模糊匹配
        matches = fuzzy_match(mod_name, names)
        if not matches or matches[0][1] < 0.3:
            print(f"{red('未找到')} MOD: {mod_name}")
            return
        matched = matches[0][0]
        if matches[0][1] < 1.0:
            print(f"  模糊匹配: {yellow(mod_name)} → {green(matched)}")

    print(f"\n{cyan('深度分析')}: {bold(matched)}")
    print("=" * 50)
    reports = deep_scan_multiple([matched])
    if not reports:
        print(f"未找到 MOD: {matched}")
        return
    if reports[0].get("error"):
        print(f"{red('错误')}: {reports[0]['error']}")
        return

    _print_report(reports[0])
    if export == "json":
        _export_json(reports)


def interactive() -> None:
    """交互模式（原 main 函数）"""
    print("星露谷物语 MOD 深度分析")
    print("=" * 50)
    print()

    start_watching()
    print()

    results = quick_scan()
    print()

    print("所有MOD列表:")
    print("-" * 50)
    for i, r in enumerate(results, 1):
        default = " [默认]" if r.get("status") in ("risk", "warning") else ""
        print(f"  [{i:2d}] {r['status_text']}{default}")
        print(f"       {r['name']} v{r['version']}  [{r['mod_type']}]")

    default_count = sum(1 for r in results if r.get("status") in ("risk", "warning"))
    print()
    print(f"共 {len(results)} 个MOD，{default_count} 个标记为需要深度分析")
    print()

    print("输入要深度分析的MOD编号（逗号分隔，如 1,3,5）")
    print(f"直接回车则分析全部 {default_count} 个标记的MOD")
    inp = input(">>> ").strip()

    if inp:
        try:
            indices = [int(x.strip()) for x in inp.split(",") if x.strip()]
            selected = [results[i-1] for i in indices if 1 <= i <= len(results)]
        except (ValueError, IndexError):
            print("输入格式错误，将分析全部标记的MOD")
            selected = [r for r in results if r.get("status") in ("risk", "warning")]
    else:
        selected = [r for r in results if r.get("status") in ("risk", "warning")]

    if not selected:
        print("没有选择任何MOD")
        if is_watching():
            stop_watching()
        return

    print()
    print(f"将对 {len(selected)} 个MOD进行深度分析:")
    for r in selected:
        print(f"  - {r['name']} v{r['version']}")
    print()

    confirm = input("确认开始深度分析？(y/n): ").strip().lower()
    if confirm != "y":
        print("已取消")
        if is_watching():
            stop_watching()
        return

    print()
    reports = deep_scan_multiple([r["name"] for r in selected])

    for report in reports:
        _print_report(report)

    if is_watching():
        stop_watching()


def main() -> None:
    Colors.setup()
    parser = argparse.ArgumentParser(
        description="星露谷物语 MOD 检查工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python scan_cli.py                       交互模式（默认）
  python scan_cli.py -q                    仅快筛
  python scan_cli.py -d "MOD名称"         深度分析指定MOD
  python scan_cli.py -q -e json            快筛并导出JSON
  python scan_cli.py -d "MOD名" -e out.json 深度分析并保存到文件
  python scan_cli.py --refresh             刷新缓存后进入交互模式
        """,
    )
    parser.add_argument("-q", "--quick", action="store_true", help="仅运行快筛")
    parser.add_argument("-d", "--deep", type=str, metavar="MOD名", help="深度分析指定MOD")
    parser.add_argument("-e", "--export", type=str, nargs="?", const="json", metavar="格式/路径",
                        help="导出结果 (默认json格式，可指定输出文件路径)")
    parser.add_argument("--refresh", action="store_true", help="先刷新N网缓存")
    parser.add_argument("--no-watch", action="store_true", help="禁用文件监听")

    args = parser.parse_args()

    # 刷新缓存
    if args.refresh:
        from nexus_api import refresh_all_cache
        refresh_all_cache()
        print()

    # 执行对应模式
    if args.quick and args.deep:
        print("不能同时指定 --quick 和 --deep")
        sys.exit(1)
    elif args.deep:
        cmd_deep(args.deep, args.export or "")
    elif args.quick:
        cmd_quick(args.export or "")
    else:
        interactive()


if __name__ == "__main__":
    main()