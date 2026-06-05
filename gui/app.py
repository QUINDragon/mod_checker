# -*- coding: utf-8 -*-
"""ModChecker 原生桌面界面"""
import tkinter as tk
from tkinter import ttk, messagebox
import threading, queue, traceback, io, sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scanner import scan_mods
from fix_mode import run_diagnosis, run_fixes, get_actions
from logger import log

BG="#0f1117";SURFACE="#1a1d27";BORDER="#2a2d3a";TEXT="#c9d1d9";DIM="#6e7681"
GREEN="#3fb950";RED="#f85149";YELLOW="#d2991d";BLUE="#58a6ff";ACCENT="#1f6feb"
DEBUG = os.environ.get("MOD_CHECK_DEBUG","").lower() in ("1","true","yes")

def setup_style():
    s=ttk.Style()
    try:s.theme_use("clam")
    except:pass
    s.configure("TFrame",background=BG)
    s.configure("TLabel",background=BG,foreground=TEXT,font=("",10))
    s.configure("TButton",background=SURFACE,foreground=TEXT,font=("",9))
    s.map("TButton",background=[("active","#252836")])
    s.configure("Accent.TButton",background=ACCENT,foreground="white")
    s.configure("TNotebook",background=BG,borderwidth=0)
    s.configure("TNotebook.Tab",background=SURFACE,foreground=DIM,padding=[16,8],font=("",10))
    s.map("TNotebook.Tab",background=[("selected",ACCENT)],foreground=[("selected","white")])
    s.configure("Treeview",background=SURFACE,foreground=TEXT,fieldbackground=SURFACE,font=("",9),rowheight=26)
    s.configure("Treeview.Heading",background=BORDER,foreground=DIM,font=("",8,"bold"))
    s.map("Treeview",background=[("selected",ACCENT)],foreground=[("selected","white")])

class App:
    def __init__(self,root):
        self.root=root;root.title("ModChecker");root.geometry("1024x680");root.configure(bg=BG);root.minsize(800,500)
        setup_style()
        self.mods=[];self.sel=None;self._q=queue.Queue()
        self._cache_mods=None;self._cache_log=None;self._cache_cp=None;self._cache_map=None
        if DEBUG:root.report_callback_exception=self._on_err
        self._ui();self._poll();self.scan()
        if DEBUG:self._log(f"DEBUG Python {sys.version.split()[0]}\n")
    def _on_err(self,*a):
        b=io.StringIO();traceback.print_exception(*a,file=b)
        self._log(f"ERROR {b.getvalue()}","err")
        messagebox.showerror("Error",str(a[1]))
    def _ui(self):
        pw=ttk.PanedWindow(self.root,orient=tk.HORIZONTAL);pw.pack(fill=tk.BOTH,expand=True)
        L=ttk.Frame(pw,width=300);pw.add(L,weight=0)
        bar=ttk.Frame(L);bar.pack(fill=tk.X,padx=8,pady=8)
        ttk.Button(bar,text="Scan",style="Accent.TButton",command=self.scan).pack(side=tk.LEFT,padx=2)
        ttk.Button(bar,text="Diagnose",command=self._diag).pack(side=tk.LEFT,padx=2)
        ttk.Button(bar,text="Refresh N网",command=self._refresh).pack(side=tk.LEFT,padx=2)
        ttk.Button(bar,text="Settings",command=self._settings).pack(side=tk.RIGHT,padx=2)
        self.search_var=tk.StringVar();self.search_var.trace_add("write",lambda*_:self._filter())
        se=tk.Entry(L,textvariable=self.search_var,bg=SURFACE,fg=TEXT,insertbackground=TEXT,relief=tk.FLAT,font=("",10))
        se.pack(fill=tk.X,ipady=6,padx=10);se.configure(highlightbackground=BORDER,highlightthickness=1)
        self.tree=ttk.Treeview(L,columns=("name","ver"),show="headings",selectmode="browse")
        self.tree.heading("name",text="MOD");self.tree.heading("ver",text="Ver");self.tree.column("name",width=180);self.tree.column("ver",width=55,anchor="e")
        self.tree.pack(fill=tk.BOTH,expand=True,padx=8,pady=4);self.tree.bind("<<TreeviewSelect>>",self._sel)
        self.st=tk.StringVar(value="Ready");tk.Label(L,textvariable=self.st,bg=SURFACE,fg=DIM,font=("",8)).pack(fill=tk.X,padx=8)
        self.log=tk.Text(L,bg="#0a0c10",fg=DIM,font=("Consolas",8),height=5,relief=tk.FLAT,state=tk.DISABLED,wrap=tk.WORD)
        self.log.pack(fill=tk.X,padx=8,pady=4)
        R=ttk.Frame(pw);pw.add(R,weight=1)
        self.nb=ttk.Notebook(R);self.nb.pack(fill=tk.BOTH,expand=True,padx=4,pady=4)
        self.tab_d=self._tab();self.tab_g=self._tab()
        self.nb.add(self.tab_d,text="Detail");self.nb.add(self.tab_g,text="Diagnose")
        self._redirect_log()
    def _tab(self):
        f=tk.Frame(self.nb,bg=BG);c=tk.Canvas(f,bg=BG,highlightthickness=0)
        s=ttk.Scrollbar(f,orient=tk.VERTICAL,command=c.yview)
        sf=tk.Frame(c,bg=BG);sf.bind("<Configure>",lambda e:c.configure(scrollregion=c.bbox("all")))
        c.create_window((0,0),window=sf,anchor="nw",tags="in")
        def _r(e):c.itemconfig("in",width=e.width)
        c.bind("<Configure>",_r);c.configure(yscrollcommand=s.set);c.pack(side=tk.LEFT,fill=tk.BOTH,expand=True);s.pack(side=tk.RIGHT,fill=tk.Y)
        f.sf=sf;return f
    def _redirect_log(self):
        import logging
        class H(logging.Handler):
            def __init__(s,g):super().__init__();s.g=g;s.setLevel(logging.DEBUG if DEBUG else logging.INFO)
            def emit(s,r):s.g.root.after(0,lambda:s.g._log(s.format(r)+"\n"))
        log.handlers.clear();h=H(self);h.setFormatter(logging.Formatter("%(levelname)-5s %(message)s"));log.addHandler(h);log.setLevel(logging.DEBUG if DEBUG else logging.INFO)
    def _log(self,msg,lvl="info"):
        try:self.log.configure(state=tk.NORMAL);self.log.insert(tk.END,msg);self.log.see(tk.END);self.log.configure(state=tk.DISABLED)
        except:pass
    def _run(self,fn,*a):
        def w():
            try:r=fn(*a);self._q.put(("ok",r,fn.__name__))
            except Exception as e:
                b=io.StringIO();traceback.print_exc(file=b);self._q.put(("err",f"{e}\n{b.getvalue()}",fn.__name__))
        threading.Thread(target=w,daemon=True).start()
    def _poll(self):
        try:
            while True:
                s,d,n=self._q.get_nowait()
                if s=="err":self._log(f"ERR {n}: {d}\n","err")
                h=getattr(self,f"_on_{n}",None)
                if h:h(d)
        except queue.Empty:pass
        self.root.after(100,self._poll)
    # SCAN
    def scan(self):
        self.st.set("Scanning...");self._run(scan_mods)
    def _on_scan_mods(self,mods):
        self.mods=mods;self._cache_mods=mods;self._cache_cp=None;self._cache_map=None;self._cache_log=None
        self.tree.delete(*self.tree.get_children())
        for i,m in enumerate(mods):
            ic="CP" if "ContentPatcher" in m.get("mod_type","") else "SM" if "SMAPI" in m.get("mod_type","") else "??"
            self.tree.insert("",tk.END,iid=str(i),values=(f"{ic} {m['name']}",m.get("version","")))
        self.st.set(f"{len(mods)} MODs")
    def _filter(self):
        q=self.search_var.get().lower()
        for i in self.tree.get_children():self.tree.detach(i)
        for i in self.tree.get_children():
            v=self.tree.item(i,"values")
            if v and q in v[0].lower():self.tree.reattach(i,"",tk.END)
    # SELECT MOD
    def _sel(self,e):
        s=self.tree.selection()
        if not s:return
        idx=int(s[0]);self.sel=self.mods[idx];self._detail(self.sel["name"])
    def _detail(self,name):
        self.st.set(f"Loading {name}...");self._run(self._load,name)
    def _load(self,name):
        mods=self._cache_mods or scan_mods()
        m=next((x for x in mods if x["name"].lower()==name.lower()),None)
        if not m:return {"error":"Not found"}
        from nexus_api import get_cached_version,get_cached_updated_time
        nid=m.get("nexus_id","")
        r={"name":m["name"],"version":m.get("version",""),"mod_type":m.get("mod_type",""),
           "quick_status":{"nexus_id":nid,"latest_version":get_cached_version(nid) if nid else None,
                           "updated_time":get_cached_updated_time(nid) if nid else None,"status_text":"cached"},
           "smapi_status":{},"deps":{"missing":[]},"conflicts":[],"mapc":[],"recs":[]}
        # SMAPI
        try:
            if self._cache_log is None:
                from mod_status import parse_smapi_log;self._cache_log=parse_smapi_log()
            ld=self._cache_log
            if ld:
                nl=name.lower()
                if any(x["name"].lower()==nl for x in ld.get("loaded_mods",[])+ld.get("loaded_packs",[])):r["smapi_status"]={"status_text":"loaded"}
                elif any(x["name"].lower()==nl for x in ld.get("skipped",[])):r["smapi_status"]={"status_text":"skipped"}
                elif any(x["name"].lower()==nl for x in ld.get("failed",[])):r["smapi_status"]={"status_text":"failed"}
        except:pass
        # CP
        if m.get("mod_type")=="ContentPatcher包":
            try:
                if self._cache_cp is None:
                    from conflict_checker.cp_analyzer import analyze_cp_mods,find_conflicts
                    self._cache_cp=find_conflicts(analyze_cp_mods(mods))
                r["conflicts"]=[c for c in(self._cache_cp or[])if m["name"]in[x["name"]for x in c.get("mods",[])]]
            except:pass
        # MAP
        try:
            if self._cache_map is None:
                from conflict_checker.map_analyzer import analyze_map_conflicts
                self._cache_map=analyze_map_conflicts(mods)
            ml=[]
            for mc in(self._cache_map or[]):
                for it in mc.get("details",[]):
                    if it.get("mod","").lower()==name.lower():
                        ml.append({"file":mc["file"],"cf": [d["mod"]for d in mc["details"]if d["mod"]!=name]});break
            r["mapc"]=ml
        except:pass
        # DEPS
        ins={x.get("unique_id","").lower()for x in mods if x.get("unique_id")}
        ms=[]
        for d in m.get("dependencies",[]):
            did=(d.get("UniqueID","")if isinstance(d,dict)else d).strip()
            if did and did.lower()not in ins:ms.append(did)
        r["deps"]["missing"]=ms
        rr=[]
        if ms:rr.append(f"Missing: {','.join(ms)}")
        if r["conflicts"]:rr.append(f"CP conflicts: {len(r['conflicts'])}")
        if r["mapc"]:rr.append(f"Map conflicts: {len(r['mapc'])}")
        if not rr:rr.append("Looks ok")
        r["recs"]=rr
        return r
    def _on__load(self,d):
        if isinstance(d,dict)and d.get("error"):self._clear(self.tab_d,f"Error: {d['error']}");return
        self._render(d);self.st.set(f"Loaded: {d.get('name','')}")
    def _render(self,d):
        f=self.tab_d.sf
        for w in f.winfo_children():w.destroy()
        tk.Label(f,text=f"{d['name']} v{d['version']}",bg=BG,fg=TEXT,font=("",13,"bold")).pack(anchor=tk.W,pady=(10,2))
        tk.Label(f,text=d.get("mod_type",""),bg=BG,fg=DIM,font=("",9)).pack(anchor=tk.W)
        qs=d.get("quick_status",{})
        self._sec(f,"Status",[("Nexus",qs.get("latest_version","?")),("Updated",(qs.get("updated_time","")or"")[:10]),("SMAPI",d.get("smapi_status",{}).get("status_text","?"))])
        ms=d.get("deps",{}).get("missing",[])
        self._sec(f,"Deps",[("Status","Missing: "+",".join(ms)if ms else"OK")])
        for c in d.get("conflicts",[])[:5]:self._sec(f,"CP Conflict",[(str(c)[:80],"")])
        for mc in d.get("mapc",[])[:5]:self._sec(f,"Map Conflict",[(f"{mc['file']} vs {','.join(mc.get('cf',[]))}","")])
        for r in d.get("recs",[]):tk.Label(f,text=f"  {r}",bg=BG,fg=DIM,font=("",9)).pack(anchor=tk.W)
    def _sec(self,p,t,rows):
        f=tk.Frame(p,bg=SURFACE,highlightbackground=BORDER,highlightthickness=1);f.pack(fill=tk.X,padx=4,pady=4)
        tk.Label(f,text=t,bg=SURFACE,fg=DIM,font=("",8,"bold")).pack(fill=tk.X,padx=10,pady=(6,2))
        for l,v in rows:
            if not l and not v:continue
            rw=tk.Frame(f,bg=SURFACE);rw.pack(fill=tk.X,padx=10,pady=1)
            tk.Label(rw,text=l,bg=SURFACE,fg=DIM,font=("",9)).pack(side=tk.LEFT)
            if v:tk.Label(rw,text=str(v),bg=SURFACE,fg=TEXT,font=("",9)).pack(side=tk.RIGHT)
    def _clear(self,tab,msg=""):
        f=tab.sf
        for w in f.winfo_children():w.destroy()
        if msg:tk.Label(f,text=msg,bg=BG,fg=DIM,font=("",12)).pack(pady=40)
    # DIAG
    def _diag(self):
        self.nb.select(self.tab_g);self.st.set("Diagnosing...")
        mods=self._cache_mods or scan_mods();self._run(run_diagnosis,{"mods":mods})
    def _on_run_diagnosis(self,dg):
        f=self.tab_g.sf
        for w in f.winfo_children():w.destroy()
        alls=dg.get("all",[])
        if not alls:tk.Label(f,text="No issues found!",bg=BG,fg=GREEN,font=("",12)).pack(pady=40);self.st.set("No issues");return

        # 按 MOD 名聚合
        by_mod:dict[str,list]={}
        for i in alls:
            mod=i.get("mod","") or "__system__"
            by_mod.setdefault(mod,[]).append(i)

        au_count=sum(1 for i in alls if i.get("category")=="auto")
        mn_count=len(alls)-au_count
        tk.Label(f,text=f"Auto-fixable: {au_count}  |  Need manual: {mn_count}  |  MODs: {len(by_mod)}",
                 bg=BG,fg=DIM,font=("",10)).pack(anchor=tk.W,pady=4)

        for mod_name,issues in by_mod.items():
            has_auto=any(i.get("category")=="auto" for i in issues)
            cat="auto" if has_auto else "manual"
            # 聚合详情
            detail=" | ".join(i.get("detail","")[:80] for i in issues[:3])
            if len(issues)>3:detail+=f" ... +{len(issues)-3} more"
            agg={"mod":mod_name,"detail":detail,"issues":issues,"category":cat,
                 "action":"fix_all" if has_auto else "manual_check"}
            self._issue_card(f,agg,cat,len(by_mod))

        self.st.set(f"Diagnose done: {len(alls)} issues in {len(by_mod)} MODs")
        self._dg=alls

    def _issue_card(self,parent,issue,cat,idx):
        """可折叠的问题卡片，多个子问题聚合，含修复按钮"""
        color=GREEN if cat=="auto" else YELLOW
        mod=issue.get("mod","System")
        subs=issue.get("issues",[issue])
        label=f"{mod} ({len(subs)} issues)" if len(subs)>1 else mod
        wrap=tk.Frame(parent,bg=SURFACE,highlightbackground=BORDER,highlightthickness=1)
        wrap.pack(fill=tk.X,padx=4,pady=2)

        collapsed=tk.BooleanVar(value=True)
        hdr=tk.Frame(wrap,bg=SURFACE,cursor="hand2")
        hdr.pack(fill=tk.X)

        toggle=tk.Label(hdr,text="",bg=SURFACE,fg=color,font=("",10),width=2,anchor=tk.W)
        toggle.pack(side=tk.LEFT,padx=(6,0))
        tk.Label(hdr,text=label,bg=SURFACE,fg=color,font=("",9,"bold")).pack(side=tk.LEFT,padx=4)
        tk.Label(hdr,text=f"{len(subs)} issue(s)",bg=SURFACE,fg=DIM,font=("",8)).pack(side=tk.LEFT,padx=4)

        if cat=="auto":
            def _do_fix(iss=issue):
                self._fix_mod_all(iss)
            tk.Button(hdr,text="Fix All",bg=ACCENT,fg="white",font=("",8),relief=tk.FLAT,bd=0,padx=8,
                      command=_do_fix,cursor="hand2").pack(side=tk.RIGHT,padx=6)

        detail_frame=tk.Frame(wrap,bg=SURFACE)

        def _toggle():
            if collapsed.get():
                detail_frame.pack(fill=tk.X,padx=10,pady=(0,8))
                toggle.configure(text="")
                collapsed.set(False)
            else:
                detail_frame.pack_forget()
                toggle.configure(text="")
                collapsed.set(True)

        hdr.bind("<Button-1>",lambda e:_toggle())
        toggle.bind("<Button-1>",lambda e:_toggle())

        for si in subs:
            ic=GREEN if si.get("category")=="auto" else YELLOW
            tk.Label(detail_frame,text=f"[{si.get('action','')}] {si.get('detail','')}",
                    bg=SURFACE,fg=ic,font=("",9),wraplength=600,justify=tk.LEFT).pack(anchor=tk.W,pady=2)

    def _fix_mod_all(self,agg):
        """修复一个 MOD 的全部自动修复问题"""
        subs=agg.get("issues",[])
        auto_subs=[s for s in subs if s.get("category")=="auto"]
        self._log(f"Fixing {len(auto_subs)} issues for {agg.get('mod','')}\n")
        self.st.set(f"Fixing {agg.get('mod','')}...")
        def _work():
            results=[]
            from fix_mode import get_actions
            acts={a.name:a for a in get_actions()}
            for s in auto_subs:
                act=acts.get(s.get("action",""))
                if act:results.append(act.fix(s,dry_run=False))
            return results
        _work.__name__="fix_all_action"
        self._run(_work)

    def _on_fix_all_action(self,results):
        ok=sum(1 for r in results if r.get("status")=="fixed")
        er=sum(1 for r in results if r.get("status")=="error")
        self._log(f"Fix done: {ok} ok, {er} failed\n")
        self.st.set(f"Fix done: {ok}/{len(results)}")
        if fx:self._sec(f,f"Fixed ({len(fx)})",[(r["message"],"")for r in fx])
        if pt:self._sec(f,f"Partial ({len(pt)})",[(r["message"],"")for r in pt])
        if er:self._sec(f,f"Error ({len(er)})",[(r["message"],"")for r in er])
        if not fx and not pt and not er:tk.Label(f,text="Nothing to fix",bg=BG,fg=GREEN,font=("",12)).pack(pady=40)
        self.st.set(f"Fix: {len(fx)} ok, {len(er)} err")
    # NEXUS
    def _refresh(self):
        from config import get_api_key
        if not get_api_key():self._log("Need API Key\n");self._settings();return
        self.st.set("Refreshing...");self._run(self._do_refresh)
    def _do_refresh(self):
        from nexus_api import refresh_all_cache
        return refresh_all_cache(silent=False)
    def _on__do_refresh(self,failed):
        n=len(failed)if isinstance(failed,list)else 0
        self._log(f"Refresh done, {n} failed\n");self.scan()
    # SETTINGS
    def _settings(self):
        from config import get_api_key,save_api_key
        d=tk.Toplevel(self.root);d.title("API Key");d.geometry("450x200");d.configure(bg=BG);d.resizable(False,False);d.transient(self.root);d.grab_set()
        tk.Label(d,text="Nexus Mods API Key",bg=BG,fg=TEXT,font=("",12,"bold")).pack(pady=(16,4))
        tk.Label(d,text="Get from nexusmods.com/users/myaccount",bg=BG,fg=DIM,font=("",8)).pack()
        frm=tk.Frame(d,bg=BG);frm.pack(fill=tk.X,padx=20,pady=10)
        kv=tk.StringVar(value=get_api_key());sv=tk.BooleanVar(value=False)
        en=tk.Entry(frm,textvariable=kv,show="*",bg=SURFACE,fg=TEXT,insertbackground=TEXT,font=("Consolas",10),relief=tk.FLAT)
        en.pack(fill=tk.X,ipady=6);en.configure(highlightbackground=BORDER,highlightthickness=1)
        def tg():en.configure(show=""if sv.get()else"*")
        tk.Checkbutton(frm,text="Show",variable=sv,command=tg,bg=BG,fg=DIM,selectcolor=BG).pack(anchor=tk.W)
        sl=tk.Label(d,text=""if get_api_key()else"Enter your key",bg=BG,fg=YELLOW,font=("",9));sl.pack()
        def svk():
            k=kv.get().strip()
            if not k:sl.configure(text="Cannot be empty",fg=RED);return
            save_api_key(k);sl.configure(text="Saved! Takes effect immediately",fg=GREEN)
            self._log(f"API Key saved\n");d.after(500,d.destroy);d.after(300,self.scan)
        bf=tk.Frame(d,bg=BG);bf.pack(pady=8)
        ttk.Button(bf,text="Save",style="Accent.TButton",command=svk).pack(side=tk.LEFT,padx=4)
        ttk.Button(bf,text="Cancel",command=d.destroy).pack(side=tk.LEFT,padx=4)

def run_gui():
    r=tk.Tk();App(r);r.mainloop()

if __name__=="__main__":run_gui()
