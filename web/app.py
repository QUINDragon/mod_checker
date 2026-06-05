"""
Web 前端 — Flask REST API + 页面
启动: python main.py web
"""
import sys, os

# 确保项目根目录在 path 中
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask, jsonify, render_template, request

from scanner import scan_mods
from deep_scan import deep_scan_multiple
from fix_mode import run_diagnosis, run_fixes, get_actions

app = Flask(__name__)


# ═══════════════════════════════════════════════════════════════
#  API 路由
# ═══════════════════════════════════════════════════════════════

@app.route("/")
def index():
    """主页"""
    return render_template("index.html")


@app.route("/api/mods")
def api_mods():
    """获取所有 MOD 列表"""
    mods = scan_mods()
    return jsonify([
        {
            "name": m.get("name", ""),
            "version": m.get("version", ""),
            "type": m.get("mod_type", ""),
            "nexus_id": m.get("nexus_id", ""),
        }
        for m in mods
    ])


@app.route("/api/mods/<name>")
def api_mod_detail(name: str):
    """单个 MOD 深度分析"""
    reports = deep_scan_multiple([name])
    if not reports or reports[0].get("error"):
        return jsonify({"error": f"未找到 MOD: {name}"}), 404
    return jsonify(reports[0])


@app.route("/api/diagnose")
def api_diagnose():
    """运行诊断"""
    mods = scan_mods()
    diag = run_diagnosis({"mods": mods})
    return jsonify({
        "total": diag["total"],
        "auto_fixable": len(diag.get("auto_fixable", [])),
        "manual": len(diag.get("manual", [])),
        "issues": diag.get("all", []),
    })


@app.route("/api/fix", methods=["POST"])
def api_fix():
    """执行修复"""
    data = request.json or {}
    dry_run = data.get("dry_run", False)
    mods = scan_mods()
    diag = run_diagnosis({"mods": mods})
    results = run_fixes(diag, dry_run=dry_run)
    return jsonify(results)


@app.route("/api/actions")
def api_actions():
    """可用修复动作列表"""
    return jsonify([
        {"name": a.name, "description": a.description, "category": a.category}
        for a in get_actions()
    ])


# ═══════════════════════════════════════════════════════════════
#  启动
# ═══════════════════════════════════════════════════════════════

def run_server(host: str = "127.0.0.1", port: int = 8090, debug: bool = False):
    """启动 Web 服务器"""
    print(f"\n🌟 ModChecker Web 前端已启动: http://{host}:{port}")
    print("   按 Ctrl+C 停止\n")
    app.run(host=host, port=port, debug=debug)


if __name__ == "__main__":
    run_server(debug=True)
