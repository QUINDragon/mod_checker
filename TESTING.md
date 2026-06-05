# ModChecker 测试流程

每次修改后按以下步骤测试，确保所有功能正常。

---

## 测试环境

- 当前工作目录: mod_check/
- MOD 目录: C:\Users\19236\AppData\Roaming\Vortex\stardewvalley\mods
- 当前版本: (从 SMAPI 日志获取)

---

## 步骤 1: 基础扫描

`powershell
cd C:\Users\19236\Desktop\work\mod_check
python -c "from scanner import scan_mods; ms=scan_mods(); print(f'扫描到 {len(ms)} 个MOD')"
`

预期结果:
- 扫描到所有 MOD（无报错）
- 每个 MOD 有 nexus_id（或正确标记为无ID）
- 不会重复扫描（缓存生效）

---

## 步骤 2: 第一层快筛

`powershell
python quick_scan.py
`

预期结果:
- 游戏版本正确显示（从 SMAPI 日志或默认值）
- 所有 MOD 有状态: ✅ / 🔴 / ⚠️ / ❓
- ❓ 数量为 0（所有 MOD 都有 N网缓存）
- 统计数字正确

---

## 步骤 3: 轻度修复

`powershell
python auto_fix/manifest_fixer.py
`

预期结果:
- 所有 MOD 的 manifest.json 检查完毕
- 修复的问题会显示（尾部逗号、版本号标准化等）
- 修复前自动备份到 auto_fix/backup/

---

## 步骤 4: CP 包冲突检测

`powershell
python conflict_checker/cp_analyzer.py
`

预期结果:
- 所有 ContentPatcher 包分析完毕
- 同压缩包内的冲突被过滤（显示 ✅ 没有发现冲突 或只显示跨包冲突）
- 冲突信息包含: target, mods 列表（name, from_file, action, priority）

---

## 步骤 5: N网刷新

### 5a: 全量刷新
`powershell
python refresh.py
`

预期结果:
- 显示正在刷新 N 个MOD
- 每个MOD显示版本号
- 刷新完成提示

### 5b: 单MOD刷新
`powershell
python refresh.py 4399
`

预期结果:
- 只刷新 ID=4399 的MOD
- 显示版本号

---

## 步骤 6: 深度分析（可选，需要手动输入）

`powershell
python scan_cli.py
`

输入: 选择 MOD 编号后按提示操作

预期结果:
- 显示所有 MOD 列表
- 默认勾选 🔴 和 ⚠️ 的 MOD
- 深度分析后显示: SMAPI状态、依赖、冲突、建议

---

## 步骤 7: MOD状态分析（需要SMAPI日志）

`powershell
python mod_status.py
`

预期结果:
- 能读取 SMAPI-latest.txt
- 显示已加载/跳过/失败的 MOD 列表

---

## 步骤 8: 修复模式（启动游戏，慎用!）

`powershell
python fix_mode.py
`

预期结果:
- 启动 Stardew Valley
- 等待游戏关闭后分析新日志

---

## 常见问题排查

| 问题 | 解决方法 |
|------|---------|
| MOD 显示 ❓ 无N网ID | 检查 manifest.json 的 UpdateKeys 字段 |
| MOD 显示 ❓ 无更新时间 | 运行 python refresh.py 或单个刷新 |
| 冲突检测误报 | 检查 ind_conflicts 的同压缩包过滤逻辑 |
| 扫描不到新添加的 MOD | 检查 Vortex 是否已部署 |

## 新增文件记录

| 日期 | 文件 | 说明 |
|------|------|------|
| 2026-06-04 | auto_fix/compatibility_patch.py | 生成兼容补丁（解决 MOD 之间冲突） |

| 2026-06-04 | data/patch_record.py | 补丁数据库模块（SQLite） |

| 2026-06-04 | auto_fix/patch_generator/update_patch.py | 版本更新补丁（显示N网链接） |
| 2026-06-04 | auto_fix/patch_generator/compatibility_patch.py | 兼容补丁（生成zip包） |

| 2026-06-04 | auto_fix/__init__.py | 统一导入入口 |
| 2026-06-04 | auto_fix/patch_generator/__init__.py | 补丁模块统一导入 |

| 2026-06-04 | file_watcher.py | 文件监听（watchdog），程序运行时实时检测MOD变化 |
