import os, json, sqlite3, datetime
from logger import log

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "patches.db")
_db_initialized = False


def _get_conn():
    """获取数据库连接，自动初始化表"""
    global _db_initialized
    if not _db_initialized:
        init_db()
        _db_initialized = True
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """初始化数据库，创建表"""
    conn = _get_conn()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS patches (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT,
            created_at TEXT NOT NULL,
            patch_type TEXT NOT NULL,
            status TEXT DEFAULT 'generated',
            mod_names TEXT NOT NULL,
            target_nexus_ids TEXT,
            conflict_target TEXT,
            zip_path TEXT,
            vortex_installed_path TEXT,
            version TEXT DEFAULT '1.0.0'
        )
    """)
    conn.commit()
    conn.close()


def add_patch(name, description, patch_type, mod_names, target_nexus_ids=None,
              conflict_target=None, zip_path=None, version="1.0.0"):
    """添加一条补丁记录"""
    conn = _get_conn()
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    mod_names_json = json.dumps(mod_names, ensure_ascii=False)
    conn.execute("""
        INSERT INTO patches (name, description, created_at, patch_type, status,
                             mod_names, target_nexus_ids, conflict_target,
                             zip_path, version)
        VALUES (?, ?, ?, ?, 'generated', ?, ?, ?, ?, ?)
    """, (name, description, now, patch_type, mod_names_json,
          target_nexus_ids, conflict_target, zip_path, version))
    conn.commit()
    patch_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    conn.close()
    return patch_id


def update_status(patch_id, status, vortex_path=None):
    """更新补丁状态"""
    conn = _get_conn()
    if vortex_path:
        conn.execute("UPDATE patches SET status=?, vortex_installed_path=? WHERE id=?",
                     (status, vortex_path, patch_id))
    else:
        conn.execute("UPDATE patches SET status=? WHERE id=?", (status, patch_id))
    conn.commit()
    conn.close()


def get_patch(patch_id):
    """获取单个补丁信息"""
    conn = _get_conn()
    row = conn.execute("SELECT * FROM patches WHERE id=?", (patch_id,)).fetchone()
    conn.close()
    if row:
        d = dict(row)
        d["mod_names"] = json.loads(d["mod_names"])
        return d
    return None


def list_patches(patch_type=None, status=None):
    """列出补丁，可按类型和状态筛选"""
    conn = _get_conn()
    sql = "SELECT * FROM patches WHERE 1=1"
    params = []
    if patch_type:
        sql += " AND patch_type=?"
        params.append(patch_type)
    if status:
        sql += " AND status=?"
        params.append(status)
    sql += " ORDER BY created_at DESC"
    rows = conn.execute(sql, params).fetchall()
    conn.close()
    results = []
    for row in rows:
        d = dict(row)
        d["mod_names"] = json.loads(d["mod_names"])
        results.append(d)
    return results


def delete_patch(patch_id):
    """删除补丁记录（同时删除zip文件）"""
    patch = get_patch(patch_id)
    if patch and patch["zip_path"] and os.path.isfile(patch["zip_path"]):
        os.remove(patch["zip_path"])
    conn = _get_conn()
    conn.execute("DELETE FROM patches WHERE id=?", (patch_id,))
    conn.commit()
    conn.close()


def patch_exists(mod_names, conflict_target=None, patch_type="compatibility"):
    """检查是否已存在相同补丁"""
    conn = _get_conn()
    mod_names_json = json.dumps(sorted(mod_names), ensure_ascii=False)
    if conflict_target:
        row = conn.execute(
            "SELECT id FROM patches WHERE mod_names=? AND conflict_target=? AND patch_type=?",
            (mod_names_json, conflict_target, patch_type)
        ).fetchone()
    else:
        row = conn.execute(
            "SELECT id FROM patches WHERE mod_names=? AND patch_type=?",
            (mod_names_json, patch_type)
        ).fetchone()
    conn.close()
    return row is not None


if __name__ == "__main__":
    init_db()
    log.info("数据库初始化完成")
    
    # 测试
    pid = add_patch(
        name="ValleyGirls_Xtardew_Abigail",
        description="解决 Valley Girls 和 Xtardew P&S 在 Portraits/Abigail 上的冲突",
        patch_type="compatibility",
        mod_names=["Valley Girls", "Xtardew P&S"],
        target_nexus_ids="10532,4399",
        conflict_target="Portraits/Abigail"
    )
    print(f"添加补丁 ID={pid}")
    
    patches = list_patches()
    print(f"共有 {len(patches)} 个补丁")
    for p in patches:
        print(f"  [{p['id']}] {p['name']} - {p['status']} ({p['patch_type']})")