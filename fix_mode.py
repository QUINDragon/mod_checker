"""
星露谷物语 MOD 修复模式
统一的诊断→修复流程，支持可扩展的修复动作注册。

用法:
    python fix_mode.py              # 交互模式
    python fix_mode.py --auto       # 全自动修复
    python fix_mode.py --dry-run    # 仅诊断，不修改
    python fix_mode.py --list       # 列出所有修复动作
    python fix_mode.py --no-game    # 跳过启动游戏（离线诊断）
    python fix_mode.py --export json  # 导出诊断结果
"""
import os, sys, subprocess, time, argparse, json
from typing import Optional

from scanner import scan_mods
from config import GAME_PATH, SMAPI_LOG
from mod_status import parse_smapi_issues
from logger import log
from cli_utils import green, red, yellow, bold, cyan, Colors

SMAPI_EXE = os.path.join(GAME_PATH, "StardewModdingAPI.exe") if GAME_PATH else ""


# ═══════════════════════════════════════════════════════════════
#  修复动作注册系统
# ═══════════════════════════════════════════════════════════════

class FixAction:
    """修复动作基类。继承并实现 diagnose / can_fix / fix 即可注册。"""
    name: str = ""
    description: str = ""
    category: str = "auto"   # auto=可自动修复, manual=需手动处理

    def diagnose(self, context: dict) -> list[dict]:
        return []

    def can_fix(self, issue: dict) -> bool:
        return True

    def fix(self, issue: dict, dry_run: bool = False) -> dict:
        return {"status": "skipped", "message": "未实现"}


_registry: list[FixAction] = []


def register(cls: type) -> type:
    """装饰器：注册一个修复动作类"""
    _registry.append(cls())
    return cls


def get_actions() -> list[FixAction]:
    return _registry


# ═══════════════════════════════════════════════════════════════
#  具体修复动作（在此添加新的修复类型）
# ═══════════════════════════════════════════════════════════════

@register
class ManifestFix(FixAction):
    name = "manifest_fix"
    description = "修复 manifest.json 的格式问题"
    category = "auto"

    def diagnose(self, context: dict) -> list[dict]:
        mods = context.get("mods", scan_mods())
        issues = []
        for m in mods:
            path = m.get("manifest_path", "")
            if not path or not os.path.isfile(path):
                continue
            try:
                import json5, json as std_json
                with open(path, "r", encoding="utf-8") as f:
                    raw = f.read()
                json5.loads(raw)
                try:
                    std_json.loads(raw)
                except std_json.JSONDecodeError as e:
                    issues.append({
                        "type": "manifest_format",
                        "mod": m["name"],
                        "path": path,
                        "detail": f"{m['name']}: JSON 格式问题 ({e.msg if hasattr(e, 'msg') else '无法解析'})"
                    })
            except Exception as e:
                log.error(f"检查 manifest 失败 [{m['name']}]: {e}")
                issues.append({
                    "type": "manifest_format",
                    "mod": m["name"],
                    "path": path,
                    "detail": f"{m['name']}: 读取 manifest 出错 - {e}"
                })
        return issues

    def fix(self, issue: dict, dry_run: bool = False) -> dict:
        if dry_run:
            return {"status": "dry_run", "message": f"将修复 {issue['mod']} 的 manifest.json"}
        try:
            from auto_fix.manifest_fixer import fix_manifest_issues
            result = fix_manifest_issues(issue["path"])
            if result["status"] == "fixed":
                return {"status": "fixed", "message": f"{issue['mod']}: {', '.join(result.get('changes', []))}"}
            return {"status": result["status"], "message": f"{issue['mod']}: {result.get('message', '未知')}"}
        except Exception as e:
            log.error(f"修复 manifest 失败 [{issue.get('mod', '?')}]: {e}")
            return {"status": "error", "message": f"{issue.get('mod', '?')}: 修复失败 - {e}"}


@register
class MissingDependencyCheck(FixAction):
    name = "missing_deps"
    description = "检查缺失的 MOD 依赖，列出 N 网链接"
    category = "manual"

    def diagnose(self, context: dict) -> list[dict]:
        mods = context.get("mods", scan_mods())
        installed = {m.get("unique_id", "").lower() for m in mods if m.get("unique_id")}
        issues = []
        for m in mods:
            for dep in m.get("dependencies", []):
                dep_id = (dep.get("UniqueID", "") if isinstance(dep, dict) else dep).strip()
                if dep_id and dep_id.lower() not in installed:
                    nexus_hint = ""
                    for mm in mods:
                        if mm.get("unique_id", "").lower() == dep_id.lower():
                            nexus_hint = mm.get("nexus_id", "")
                            break
                    issues.append({
                        "type": "missing_dependency",
                        "mod": m["name"],
                        "missing_id": dep_id,
                        "nexus_hint": nexus_hint,
                        "detail": f"{m['name']} 缺少依赖: {dep_id}"
                    })
        return issues


@register
class SmapiLogIssue(FixAction):
    name = "smapi_log"
    description = "从 SMAPI 日志发现加载失败 / 被跳过的问题"
    category = "manual"

    def diagnose(self, context: dict) -> list[dict]:
        issues = parse_smapi_issues()
        return [{
            "type": "smapi_" + iss["type"].replace(" ", "_"),
            "mod": iss.get("mod", ""),
            "detail": f"{iss.get('mod', '')}: {iss.get('detail', '')}",
            "raw": iss.get("raw", "")
        } for iss in issues]


@register
class UpdateAvailable(FixAction):
    name = "update_available"
    description = "检测有 N 网新版本的 MOD，生成更新引导补丁"
    category = "auto"

    def diagnose(self, context: dict) -> list[dict]:
        mods = context.get("mods", scan_mods())
        from nexus_api import get_cached_version
        from compatibility import compare_versions
        issues = []
        for m in mods:
            nexus_id = m.get("nexus_id", "")
            if not nexus_id:
                continue
            latest = get_cached_version(nexus_id)
            lv = m.get("version", "")
            if latest and compare_versions(lv, latest) == "有可用更新":
                issues.append({
                    "type": "update_available",
                    "mod": m["name"],
                    "local_version": m.get("version", ""),
                    "latest_version": latest,
                    "nexus_id": nexus_id,
                    "detail": f"{m['name']} v{m.get('version')} → N网 v{latest}"
                })
        return issues

    def fix(self, issue: dict, dry_run: bool = False) -> dict:
        if dry_run:
            return {"status": "dry_run", "message": f"将为 {issue['mod']} 生成更新补丁"}
        try:
            from auto_fix.patch_generator.update_patch import create_update_patch
            mod = {"name": issue["mod"], "nexus_id": issue["nexus_id"], "version": issue["local_version"]}
            result = create_update_patch(mod)
            if result.get("status") == "success":
                return {"status": "fixed", "message": f"{issue['mod']}: {result.get('message', '已生成更新补丁')}"}
            return {"status": result.get("status", "error"), "message": f"{issue['mod']}: {result.get('message', '')}"}
        except Exception as e:
            log.error(f"生成更新补丁失败 [{issue.get('mod', '?')}]: {e}")
            return {"status": "error", "message": f"{issue.get('mod', '?')}: 更新补丁生成失败 - {e}"}


@register
class CPConflictCheck(FixAction):
    name = "cp_conflict"
    description = "检测 Content Patcher 包的资源冲突，可生成兼容补丁"
    category = "auto"

    def diagnose(self, context: dict) -> list[dict]:
        mods = context.get("mods", scan_mods())
        try:
            from conflict_checker.cp_analyzer import analyze_cp_mods, find_conflicts
            results = analyze_cp_mods(mods)
            conflicts = find_conflicts(results)
            issues = []
            for c in conflicts:
                names = [m["name"] for m in c["mods"]]
                issues.append({
                    "type": "cp_conflict",
                    "mod": names[0] if names else "",
                    "conflict": c,
                    "detail": f"CP 冲突: {c['target']} (涉及 {', '.join(names)})"
                })
            return issues
        except Exception as e:
            log.error(f"CP 冲突检测失败: {e}")
            return [{"type": "cp_conflict", "mod": "", "detail": f"CP 冲突检测出错: {e}"}]

    def fix(self, issue: dict, dry_run: bool = False) -> dict:
        conflict = issue.get("conflict", {})
        mod_name = issue.get("mod", "")
        if not conflict or not mod_name:
            return {"status": "skipped", "message": "缺少冲突信息，无法生成补丁"}
        if dry_run:
            names = [m["name"] for m in conflict.get("mods", [])]
            return {"status": "dry_run", "message": f"将为 {', '.join(names)} 生成兼容补丁"}
        try:
            from auto_fix.patch_generator.compatibility_patch import generate_compatibility_patch
            result = generate_compatibility_patch(conflict, mod_name)
            if result.get("status") == "success":
                return {"status": "fixed", "message": result.get("message", f"已为 {mod_name} 生成兼容补丁")}
            return {"status": result.get("status", "error"), "message": f"{mod_name}: {result.get('message', '')}"}
        except Exception as e:
            log.error(f"生成兼容补丁失败 [{mod_name}]: {e}")
            return {"status": "error", "message": f"{mod_name}: 兼容补丁生成失败 - {e}"}


@register
class MapConflictCheck(FixAction):
    name = "map_conflict"
    description = "检测地图文件冲突（多个 MOD 修改同一地图）"
    category = "manual"

    def diagnose(self, context: dict) -> list[dict]:
        mods = context.get("mods", scan_mods())
        try:
            from conflict_checker.map_analyzer import analyze_map_conflicts
            conflicts = analyze_map_conflicts(mods)
            issues = []
            for c in conflicts:
                mod_names = [d["mod"] for d in c["details"]]
                issues.append({
                    "type": "map_conflict",
                    "mod": mod_names[0] if mod_names else "",
                    "detail": f"地图冲突: {c['file']} ({', '.join(mod_names)})"
                })
            return issues
        except Exception as e:
            log.error(f"地图冲突检测失败: {e}")
            return [{"type": "map_conflict", "mod": "", "detail": f"地图冲突检测出错: {e}"}]


@register
class SmapiVersionCheck(FixAction):
    name = "smapi_version"
    description = "检查 SMAPI 版本是否满足 MOD 的要求"
    category = "manual"

    def diagnose(self, context: dict) -> list[dict]:
        mods = context.get("mods", scan_mods())
        try:
            from compatibility import check_smapi_compatibility
            issues = []
            for m in mods:
                min_api = m.get("min_api", "")
                if min_api:
                    result = check_smapi_compatibility(min_api)
                    if result.get("compatible") is False:
                        issues.append({
                            "type": "smapi_version_low",
                            "mod": m["name"],
                            "detail": f"{m['name']} 需要 SMAPI v{min_api}，{result['reason']}"
                        })
            return issues
        except Exception as e:
            log.error(f"SMAPI 版本检查失败: {e}")
            return [{"type": "smapi_version_low", "mod": "", "detail": f"SMAPI 版本检查出错: {e}"}]


# OutdatedModCheck已移除——快筛和ContentRescue已覆盖其功能
@register
class NullSafetyCheck(FixAction):
    name = "null_safety"
    description = "检测 MOD 文件中的空指针风险：manifest 缺字段、content.json 空 Target、SMAPI NullReferenceException"
    category = "auto"

    def diagnose(self, context: dict) -> list[dict]:
        mods = context.get("mods", scan_mods())
        issues = []

        for m in mods:
            path = m.get("manifest_path", "")
            if not path or not os.path.isfile(path):
                continue

            try:
                import json5
                with open(path, "r", encoding="utf-8") as f:
                    raw = f.read()
                data = json5.loads(raw)
            except Exception:
                continue

            null_problems = []

            # 1. 检查 manifest 必填字段
            for field in ["Name", "UniqueID", "Version"]:
                val = data.get(field)
                if val is None or (isinstance(val, str) and not val.strip()):
                    null_problems.append(f"manifest 缺少必填字段: {field}")

            # 2. 检查 MOD 类型标识（EntryDll 或 ContentPackFor 至少一个）
            has_entry = data.get("EntryDll") and isinstance(data.get("EntryDll"), str) and data["EntryDll"].strip()
            has_cp = (data.get("ContentPackFor") and
                      isinstance(data.get("ContentPackFor"), dict) and
                      data["ContentPackFor"].get("UniqueID"))
            if not has_entry and not has_cp:
                null_problems.append("manifest 未指定 EntryDll 或 ContentPackFor（MOD 无法被 SMAPI 识别）")

            # 3. Content Patcher 包：检查 content.json 的空指针
            if has_cp and data["ContentPackFor"]["UniqueID"] == "Pathoschild.ContentPatcher":
                cp_issues = self._check_cp_content(mods, m)
                null_problems.extend(cp_issues)

            if null_problems:
                issues.append({
                    "type": "null_safety",
                    "mod": m["name"],
                    "path": path,
                    "problems": null_problems,
                    "detail": f"{m['name']}: {'; '.join(null_problems)}"
                })

        # 4. 从 SMAPI 日志检测 NullReferenceException
        smapi_nre = self._check_smapi_null_errors()
        for sn in smapi_nre:
            issues.append(sn)

        return issues

    def _check_cp_content(self, mods: list[dict], mod: dict) -> list[str]:
        """检查 Content Patcher 包的 content.json 是否有空 Target/FromFile"""
        problems = []
        # 找到 content.json 路径
        manifest_dir = os.path.dirname(mod.get("manifest_path", ""))
        for candidate in ["content.json", "Content.json"]:
            cp = os.path.join(manifest_dir, candidate)
            if not os.path.isfile(cp):
                continue
            try:
                import json5
                with open(cp, "r", encoding="utf-8") as f:
                    data = json5.loads(f.read())
                changes = data.get("Changes", [])
                for i, ch in enumerate(changes):
                    # 检查 Target 为空
                    target = ch.get("Target", "")
                    if not target or not str(target).strip():
                        problems.append(f"content.json 第 {i+1} 个 Change 的 Target 为空")
                    # 检查 Load 动作的 FromFile
                    action = ch.get("Action", "")
                    if action in ("Load", "EditImage") and not ch.get("FromFile", ""):
                        problems.append(f"content.json 第 {i+1} 个 Change ({action}) 缺少 FromFile")
                break  # 只检查找到的第一个
            except Exception:
                pass
        return problems

    def _check_smapi_null_errors(self) -> list[dict]:
        """从 SMAPI 日志检测 NullReferenceException"""
        from config import SMAPI_LOG
        if not os.path.isfile(SMAPI_LOG):
            return []
        try:
            with open(SMAPI_LOG, "r", encoding="utf-8") as f:
                content = f.read()

            # 匹配 NullReferenceException
            import re
            issues = []
            for m in re.finditer(r"NullReferenceException", content):
                # 取这一行和下一行作为上下文
                start = max(0, m.start() - 200)
                end = min(len(content), m.end() + 300)
                ctx = content[start:end].replace("\n", " ").strip()[:200]
                issues.append({
                    "type": "null_safety",
                    "mod": "",
                    "detail": f"SMAPI 日志发现 NullReferenceException: {ctx}..."
                })
            return issues
        except Exception:
            return []

    def fix(self, issue: dict, dry_run: bool = False) -> dict:
        """尝试修复空指针问题：给缺失的必填字段填默认值"""
        path = issue.get("path", "")
        problems = issue.get("problems", [])
        if not path or not problems:
            return {"status": "skipped", "message": f"{issue['mod']}: 无可修复的空指针问题"}

        # 只能修复 manifest 缺字段的问题，content.json 和 NullReferenceException 无法自动修
        fixable = [p for p in problems if "manifest 缺少必填字段" in p]
        unfixable = [p for p in problems if p not in fixable]

        if not fixable:
            return {"status": "manual", "message": f"{issue['mod']}: 空指针问题需手动修复 ({'; '.join(problems)})"}

        if dry_run:
            return {"status": "dry_run", "message": f"将为 {issue['mod']} 补全必填字段"}

        try:
            import json5, json as std_json
            with open(path, "r", encoding="utf-8") as f:
                raw = f.read()
            data = json5.loads(raw)

            fixed_fields = []
            # Name 缺失 → 用文件夹名
            if not data.get("Name"):
                folder = os.path.basename(os.path.dirname(path))
                data["Name"] = folder
                fixed_fields.append(f"Name={folder}")
            # UniqueID 缺失 → 用 Name 生成
            if not data.get("UniqueID"):
                name = data.get("Name", os.path.basename(os.path.dirname(path)))
                data["UniqueID"] = name.replace(" ", ".").replace("[", "").replace("]", "")
                fixed_fields.append(f"UniqueID={data['UniqueID']}")
            # Version 缺失 → 默认 1.0.0
            if not data.get("Version"):
                data["Version"] = "1.0.0"
                fixed_fields.append("Version=1.0.0")

            if fixed_fields:
                from auto_fix.backup import backup_file
                backup_file(path)
                with open(path, "w", encoding="utf-8") as f:
                    std_json.dump(data, f, ensure_ascii=False, indent=4)

            msg = f"{issue['mod']}: 补全必填字段 ({', '.join(fixed_fields)})" if fixed_fields else ""
            if unfixable:
                msg += f" | 仍需手动处理: {'; '.join(unfixable)}"
            return {"status": "partial" if unfixable else "fixed", "message": msg}
        except Exception as e:
            return {"status": "error", "message": f"{issue['mod']}: 修复失败 - {e}"}


@register
class MissingAssetCheck(FixAction):
    name = "missing_asset"
    description = "检测 CP 包的 FromFile 指向的资源文件是否真实存在"
    category = "manual"

    def diagnose(self, context: dict) -> list[dict]:
        mods = context.get("mods", scan_mods())
        issues = []
        for m in mods:
            if m.get("mod_type") != "ContentPatcher包":
                continue
            path = m.get("manifest_path", "")
            if not path:
                continue
            manifest_dir = os.path.dirname(path)
            try:
                from conflict_checker.cp_analyzer import get_cp_content_path, extract_changes
                content_path = get_cp_content_path(m)
                if not content_path:
                    continue
                changes = extract_changes(content_path)
                missing = []
                for ch in changes:
                    from_file = ch.get("from_file", "")
                    if from_file:
                        abs_path = os.path.normpath(os.path.join(os.path.dirname(content_path), from_file))
                        if not os.path.isfile(abs_path):
                            missing.append(f"{from_file} (Target: {ch.get('target', '?')})")
                if missing:
                    issues.append({
                        "type": "missing_asset",
                        "mod": m["name"],
                        "detail": f"{m['name']}: {len(missing)} 个资源文件缺失 ({'; '.join(missing[:3])}{'...' if len(missing) > 3 else ''})"
                    })
            except Exception:
                pass
        return issues


@register
class DuplicateModCheck(FixAction):
    name = "duplicate_mod"
    description = "检测相同 UniqueID 的 MOD 是否被安装了多次"
    category = "manual"

    def diagnose(self, context: dict) -> list[dict]:
        mods = context.get("mods", scan_mods())
        uid_map: dict[str, list[dict]] = {}
        for m in mods:
            uid = m.get("unique_id", "").strip()
            if uid:
                uid_map.setdefault(uid.lower(), []).append(m)

        issues = []
        for uid, ms in uid_map.items():
            if len(ms) > 1:
                versions = [f"{m['name']} v{m.get('version', '?')}" for m in ms]
                issues.append({
                    "type": "duplicate_mod",
                    "mod": ms[0]["name"],
                    "detail": f"UniqueID '{uid}' 有 {len(ms)} 个实例: {', '.join(versions)}"
                })
        return issues


@register
class EncodingCheck(FixAction):
    name = "encoding"
    description = "检测 manifest.json 是否为 UTF-8 编码（非 UTF-8 会导致中文名乱码）"
    category = "auto"

    def diagnose(self, context: dict) -> list[dict]:
        mods = context.get("mods", scan_mods())
        issues = []
        for m in mods:
            path = m.get("manifest_path", "")
            if not path or not os.path.isfile(path):
                continue
            try:
                # 尝试用 UTF-8 读取
                with open(path, "r", encoding="utf-8") as f:
                    content = f.read()
                # 检查是否包含乱码特征（不可打印的替换字符）
                if "\ufffd" in content:
                    issues.append({
                        "type": "encoding",
                        "mod": m["name"],
                        "path": path,
                        "detail": f"{m['name']}: manifest.json 不是 UTF-8 编码，存在乱码"
                    })
                # 检查是否有 BOM 头
                elif content.startswith("\ufeff"):
                    issues.append({
                        "type": "encoding",
                        "mod": m["name"],
                        "path": path,
                        "detail": f"{m['name']}: manifest.json 包含 BOM 头，可能导致解析问题"
                    })
            except UnicodeDecodeError:
                issues.append({
                    "type": "encoding",
                    "mod": m["name"],
                    "path": path,
                    "detail": f"{m['name']}: manifest.json 编码不是 UTF-8"
                })
            except Exception:
                pass
        return issues

    def fix(self, issue: dict, dry_run: bool = False) -> dict:
        path = issue.get("path", "")
        if not path or not os.path.isfile(path):
            return {"status": "error", "message": f"{issue['mod']}: 文件不存在"}
        if dry_run:
            return {"status": "dry_run", "message": f"将 {issue['mod']} 的 manifest 转码为 UTF-8"}
        try:
            # 尝试自动检测编码并转 UTF-8
            with open(path, "rb") as f:
                raw = f.read()
            # 尝试常见编码
            for enc in ["utf-8-sig", "gbk", "shift-jis", "latin-1"]:
                try:
                    text = raw.decode(enc)
                    if enc != "utf-8":
                        from auto_fix.backup import backup_file
                        backup_file(path)
                        with open(path, "w", encoding="utf-8") as f:
                            f.write(text)
                        return {"status": "fixed", "message": f"{issue['mod']}: 已从 {enc} 转码为 UTF-8"}
                    break
                except Exception:
                    continue
            return {"status": "error", "message": f"{issue['mod']}: 无法识别编码"}
        except Exception as e:
            return {"status": "error", "message": f"{issue['mod']}: 转码失败 - {e}"}


@register
class ContentRescue(FixAction):
    name = "content_rescue"
    description = "尝试让加载失败的 MOD 恢复可用：修复 manifest、修正 API 版本、生成兼容补丁"
    category = "auto"

    def diagnose(self, context: dict) -> list[dict]:
        """综合诊断：SMAPI日志中的失败/跳过 + manifest 检查 + 更新检测"""
        mods = context.get("mods", scan_mods())
        issues = []
        smapi_issues = parse_smapi_issues()

        # 建立 MOD 名称到信息的索引
        mod_map = {}
        for m in mods:
            mod_map[m["name"].lower()] = m

        # 处理 SMAPI 日志中报告的失败/跳过
        problem_names = set()
        for iss in smapi_issues:
            name = iss.get("mod", "").strip().lower()
            if name:
                problem_names.add(name)

        for name_lower in problem_names:
            mod = mod_map.get(name_lower)
            if not mod:
                continue

            actions_taken = []
            path = mod.get("manifest_path", "")

            # 1. 检查 manifest 格式
            if path and os.path.isfile(path):
                try:
                    import json5, json as std_json
                    with open(path, "r", encoding="utf-8") as f:
                        raw = f.read()
                    json5.loads(raw)
                    try:
                        std_json.loads(raw)
                    except std_json.JSONDecodeError:
                        actions_taken.append("修复 manifest 格式")
                except Exception:
                    actions_taken.append("manifest 文件异常")

            # 2. 检查是否有可用的更新
            nexus_id = mod.get("nexus_id", "")
            nexus_url = ""
            if nexus_id:
                from nexus_api import get_cached_version
                latest = get_cached_version(nexus_id)
                if latest and latest != mod.get("version", ""):
                    nexus_url = f"https://www.nexusmods.com/stardewvalley/mods/{nexus_id}"
                    actions_taken.append(f"N网有新版本 v{latest}")

            # 3. 检查依赖
            missing_deps = []
            for dep in mod.get("dependencies", []):
                dep_id = (dep.get("UniqueID", "") if isinstance(dep, dict) else dep).strip()
                if dep_id:
                    found = any(m.get("unique_id", "").lower() == dep_id.lower() for m in mods)
                    if not found:
                        missing_deps.append(dep_id)
            if missing_deps:
                actions_taken.append(f"缺失依赖: {', '.join(missing_deps)}")

            # 4. 检查 SMAPI API 版本
            min_api = mod.get("min_api", "")
            api_fixable = False
            if min_api:
                try:
                    from compatibility import _parse_version, get_local_smapi_version
                    mod_api = _parse_version(min_api)
                    local_smapi = get_local_smapi_version()
                    if local_smapi and mod_api:
                        smapi_parts = _parse_version(local_smapi)
                        if smapi_parts and any(mod_api[i] > smapi_parts[i] for i in range(min(len(mod_api), len(smapi_parts)))):
                            actions_taken.append(f"MinimumApiVersion ({min_api}) 高于当前 SMAPI — 将尝试调低")
                            api_fixable = True
                except Exception:
                    pass

            # 5. 检查 Content Patcher Format 版本
            cp_format_fixable = False
            if mod.get("mod_type") == "ContentPatcher包":
                try:
                    import json5
                    manifest_dir = os.path.dirname(path)
                    for cfile in ["content.json", "Content.json"]:
                        cpath = os.path.join(manifest_dir, cfile)
                        if os.path.isfile(cpath):
                            with open(cpath, "r", encoding="utf-8") as f:
                                cdata = json5.loads(f.read())
                            fmt = str(cdata.get("Format", "1.0"))
                            if fmt < "1.30":
                                actions_taken.append(f"content.json Format 过旧 ({fmt} → 1.30)")
                                cp_format_fixable = True
                            break
                except Exception:
                    pass

            if actions_taken:
                issues.append({
                    "type": "content_rescue",
                    "mod": mod["name"],
                    "path": path,
                    "nexus_id": nexus_id,
                    "nexus_url": nexus_url,
                    "local_version": mod.get("version", ""),
                    "api_fixable": api_fixable,
                    "cp_format_fixable": cp_format_fixable,
                    "min_api": min_api,
                    "actions": actions_taken,
                    "detail": f"{mod['name']}: {'; '.join(actions_taken)}"
                })

        return issues

    def fix(self, issue: dict, dry_run: bool = False) -> dict:
        if dry_run:
            return {"status": "dry_run",
                    "message": f"将尝试修复 {issue['mod']} ({'; '.join(issue.get('actions', []))})"}

        fixed = []
        failed = []

        # 修复 1: manifest 格式
        path = issue.get("path", "")
        if path and os.path.isfile(path):
            try:
                from auto_fix.manifest_fixer import fix_manifest_issues
                result = fix_manifest_issues(path)
                if result["status"] == "fixed":
                    fixed.append(f"manifest: {', '.join(result.get('changes', []))}")
                elif result["status"] == "no_change":
                    pass  # 无需修复也算成功
                else:
                    failed.append(f"manifest: {result.get('message', '未知')}")
            except Exception as e:
                failed.append(f"manifest 修复异常: {e}")

        # 修复 2: 修正 MinimumApiVersion
        if issue.get("api_fixable") and path and os.path.isfile(path):
            try:
                import json as std_json
                from compatibility import get_local_smapi_version
                local_smapi = get_local_smapi_version()
                if local_smapi:
                    with open(path, "r", encoding="utf-8") as f:
                        data = std_json.load(f)
                    old_api = data.get("MinimumApiVersion", "")
                    data["MinimumApiVersion"] = local_smapi
                    from auto_fix.backup import backup_file
                    backup_file(path)
                    with open(path, "w", encoding="utf-8") as f:
                        std_json.dump(data, f, ensure_ascii=False, indent=4)
                    fixed.append(f"MinimumApiVersion: {old_api} → {local_smapi}")
            except Exception as e:
                failed.append(f"修正 MinimumApiVersion 失败: {e}")

        # 修复 3: 生成更新补丁
        nexus_id = issue.get("nexus_id", "")
        if nexus_id:
            from nexus_api import get_cached_version
            latest = get_cached_version(nexus_id)
            if latest and latest != issue.get("local_version", ""):
                try:
                    from auto_fix.patch_generator.update_patch import create_update_patch
                    mod = {"name": issue["mod"], "nexus_id": nexus_id, "version": issue.get("local_version", "")}
                    result = create_update_patch(mod)
                    if result.get("status") == "success":
                        fixed.append(f"更新补丁: {result.get('message', '已生成')}")
                except Exception as e:
                    failed.append(f"更新补丁: {e}")

        # 修复 4: 升级 Content Patcher Format
        if issue.get("cp_format_fixable") and path:
            try:
                import json as std_json
                manifest_dir = os.path.dirname(path)
                for cfile in ["content.json", "Content.json"]:
                    cpath = os.path.join(manifest_dir, cfile)
                    if os.path.isfile(cpath):
                        with open(cpath, "r", encoding="utf-8") as f:
                            cdata = std_json.load(f)
                        old_fmt = cdata.get("Format", "1.0")
                        cdata["Format"] = "1.30.0"
                        from auto_fix.backup import backup_file
                        backup_file(cpath)
                        with open(cpath, "w", encoding="utf-8") as f:
                            std_json.dump(cdata, f, ensure_ascii=False, indent=4)
                        fixed.append(f"content.json Format: {old_fmt} → 1.30.0")
                        break
            except Exception as e:
                failed.append(f"Format 升级失败: {e}")

        # 构建结果消息
        parts = []
        if fixed:
            parts.append(f"已修复 {len(fixed)} 项: {' | '.join(fixed)}")
        if failed:
            parts.append(f"失败 {len(failed)} 项: {' | '.join(failed)}")
        if issue.get("nexus_url"):
            parts.append(f"手动更新: {issue['nexus_url']}")

        if not parts:
            return {"status": "skipped", "message": f"{issue['mod']}: 未找到可执行的操作"}

        status = "fixed" if fixed and not failed else "partial" if fixed else "error"
        return {"status": status, "message": f"{issue['mod']}: {'; '.join(parts)}"}


# ═══════════════════════════════════════════════════════════════
#  辅助
# ═══════════════════════════════════════════════════════════════

def run_game_for_log() -> bool:
    """启动游戏等待加载，然后关闭"""
    if not os.path.isfile(SMAPI_EXE):
        log.error(f"找不到 SMAPI: {SMAPI_EXE}")
        return False
    log.info(f"启动游戏: {SMAPI_EXE}")
    log.info("等待15秒...")
    try:
        process = subprocess.Popen([SMAPI_EXE], cwd=GAME_PATH)
        time.sleep(15)
        log.info("关闭游戏...")
        subprocess.run(["taskkill", "/f", "/im", "Stardew Valley.exe"],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=5)
        subprocess.run(["taskkill", "/f", "/im", "StardewModdingAPI.exe"],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=5)
        log.info("游戏已关闭")
        return os.path.isfile(SMAPI_LOG)
    except Exception as e:
        log.error(f"启动失败: {e}")
        return False


# ═══════════════════════════════════════════════════════════════
#  主流程
# ═══════════════════════════════════════════════════════════════

def run_diagnosis(context: dict) -> dict:
    """运行所有修复动作的诊断，返回分类后的问题列表"""
    log.info("正在诊断...")
    all_issues = []
    for action in get_actions():
        log.debug(f"  诊断: {action.name}")
        issues = action.diagnose(context)
        for iss in issues:
            iss["action"] = action.name
            iss["category"] = action.category
        all_issues.extend(issues)

    auto_issues = [i for i in all_issues if i.get("category") == "auto"]
    manual_issues = [i for i in all_issues if i.get("category") == "manual"]
    log.info(f"诊断完成: {len(auto_issues)} 可自动修复, {len(manual_issues)} 需手动")
    return {"total": len(all_issues), "auto_fixable": auto_issues, "manual": manual_issues, "all": all_issues}


def run_fixes(diagnosis: dict, dry_run: bool = False) -> list[dict]:
    """对可自动修复的问题执行修复"""
    actions = {a.name: a for a in get_actions()}
    results = []
    for issue in diagnosis.get("auto_fixable", []):
        action = actions.get(issue.get("action", ""))
        if not action:
            results.append({"status": "skipped", "message": f"未知动作: {issue.get('action')}"})
            continue
        log.info(f"修复: [{action.name}] {issue.get('detail', issue.get('mod', ''))}")
        result = action.fix(issue, dry_run=dry_run)
        result["issue"] = issue
        results.append(result)
    return results


def _print_diagnosis(diag: dict) -> None:
    """格式化打印诊断结果"""
    print("\n" + "=" * 50)
    print("  诊断报告")
    print("=" * 50)
    auto, manual = diag["auto_fixable"], diag["manual"]

    print(f"\n🔧 可自动修复 ({len(auto)}):")
    if auto:
        for i, iss in enumerate(auto, 1):
            print(f"  {i}. [{iss['action']}] {iss.get('detail', iss.get('mod', ''))}")
    else:
        print("  (无)")

    print(f"\n⚠️ 需手动处理 ({len(manual)}):")
    if manual:
        for i, iss in enumerate(manual, 1):
            print(f"  {i}. [{iss['action']}] {iss.get('detail', iss.get('mod', ''))}")
            if iss.get("type") == "missing_dependency" and iss.get("nexus_hint"):
                print(f"     N网: https://www.nexusmods.com/stardewvalley/mods/{iss['nexus_hint']}")
    else:
        print("  (无)")
    if not auto and not manual:
        print("\n✅ 没有发现任何问题！")


def _print_results(results: list[dict]) -> None:
    """格式化打印修复结果"""
    print("\n" + "=" * 50)
    print("  修复结果")
    print("=" * 50)
    fixed = [r for r in results if r["status"] == "fixed"]
    partial = [r for r in results if r["status"] == "partial"]
    dry = [r for r in results if r["status"] == "dry_run"]
    errors = [r for r in results if r["status"] == "error"]
    if dry:
        print(f"\n🔍 预览 ({len(dry)}):")
        for r in dry:
            print(f"  → {r['message']}")
    if fixed:
        print(f"\n✅ 已修复 ({len(fixed)}):")
        for r in fixed:
            print(f"  ✓ {r['message']}")
    if partial:
        print(f"\n⚠️ 部分修复 ({len(partial)}):")
        for r in partial:
            print(f"  ~ {r['message']}")
    if errors:
        print(f"\n❌ 失败 ({len(errors)}):")
        for r in errors:
            print(f"  ✗ {r['message']}")


# ═══════════════════════════════════════════════════════════════
#  CLI 入口
# ═══════════════════════════════════════════════════════════════

def main() -> None:
    Colors.setup()
    parser = argparse.ArgumentParser(description="星露谷物语 MOD 修复模式")
    parser.add_argument("--auto", action="store_true", help="全自动修复，不询问")
    parser.add_argument("--dry-run", action="store_true", help="仅诊断，不修改")
    parser.add_argument("--no-game", action="store_true", help="跳过启动游戏")
    parser.add_argument("--list", action="store_true", help="列出所有修复动作")
    parser.add_argument("--export", type=str, nargs="?", const="json", metavar="路径",
                        help="导出诊断结果为 JSON")
    args = parser.parse_args()

    if args.list:
        print("可用的修复动作:")
        for a in get_actions():
            tag = "🔧" if a.category == "auto" else "⚠️"
            print(f"  {tag} {a.name}: {a.description}")
        return

    print("星露谷物语 MOD 修复模式")
    print("=" * 50)
    if args.dry_run:
        print("⚠️  仅诊断模式，不会做任何修改")
    print()

    # 扫描
    log.info("扫描本地 MOD...")
    mods = scan_mods()
    context = {"mods": mods}
    log.info(f"共 {len(mods)} 个 MOD")

    # 第一轮诊断（不需要游戏）
    diag = run_diagnosis(context)

    # 启动游戏获取日志
    if not args.no_game:
        print()
        if run_game_for_log():
            diag2 = run_diagnosis(context)
            diag["auto_fixable"].extend(diag2["auto_fixable"])
            diag["manual"].extend(diag2["manual"])
            diag["all"].extend(diag2["all"])
            diag["total"] = len(diag["all"])

    # 打印
    _print_diagnosis(diag)

    # 导出
    if args.export:
        path = args.export if args.export != "json" else None
        out = json.dumps(diag["all"], ensure_ascii=False, indent=2)
        if path and path != "json":
            with open(path, "w", encoding="utf-8") as f:
                f.write(out)
            print(f"\n已导出到: {path}")
        else:
            print("\n" + out)

    if not diag["auto_fixable"]:
        if diag["manual"]:
            print("\n以上问题需要手动处理。")
        return

    if not args.auto:
        print()
        c = input(f"确认修复 {len(diag['auto_fixable'])} 个问题？(y/n): ").strip().lower()
        if c != "y":
            print("已取消")
            return

    print()
    results = run_fixes(diag, dry_run=args.dry_run)
    _print_results(results)

    # 自动保存修复报告
    _save_report(diag, results)

    if diag["manual"]:
        print(f"\n还有 {len(diag['manual'])} 个问题需要手动处理。")
    print(f"\n{green('完成!')}")


def _save_report(diag: dict, results: list[dict]) -> None:
    """自动保存修复报告到 reports/ 目录"""
    try:
        import datetime as dt
        reports_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "reports")
        os.makedirs(reports_dir, exist_ok=True)
        ts = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
        path = os.path.join(reports_dir, f"fix_report_{ts}.json")
        report = {
            "time": ts,
            "diagnosis": {
                "total": diag["total"],
                "auto_fixable": len(diag.get("auto_fixable", [])),
                "manual": len(diag.get("manual", [])),
            },
            "issues": diag.get("all", []),
            "results": results,
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        print(f"\n{cyan('报告已保存')}: {path}")
    except Exception:
        pass


if __name__ == "__main__":
    main()