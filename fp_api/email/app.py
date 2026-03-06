import os, re, uuid, tempfile, threading, imaplib, email, datetime
from email.header import decode_header
from email.utils import parsedate_to_datetime
from functools import wraps
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import jwt
from werkzeug.utils import secure_filename
from dateutil.relativedelta import relativedelta

from models import db, User, InvoiceRecord
from ai_service import parse_invoice_with_qwen
from invoice_parser import parse_invoice_result_to_row, INVOICE_COLUMNS
from excel_utils import build_excel

_root = os.path.dirname(os.path.abspath(__file__))
_static = os.path.join(_root, "frontend", "dist")
if os.path.isdir(_static):
    app = Flask(__name__, static_folder=_static, static_url_path="")
else:
    app = Flask(__name__, static_folder="web", static_url_path="")
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "smart-invoice-dev-secret-change-in-prod")
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get(
    "DATABASE_URI", "sqlite:///" + os.path.join(os.path.dirname(os.path.abspath(__file__)), "data.db")
)
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
CORS(app, supports_credentials=True)
db.init_app(app)

# 统一目录初始化
BASE_DIR = os.path.join(tempfile.gettempdir(), "smart_invoice_pro_v9")
PREVIEW_DIR = os.path.join(BASE_DIR, "preview")
ORIGIN_DIR = os.path.join(BASE_DIR, "origin")
EXCEL_DIR = os.path.join(BASE_DIR, "excel")
for d in [PREVIEW_DIR, ORIGIN_DIR, EXCEL_DIR]:
    os.makedirs(d, exist_ok=True)

TASKS = {}
TASKS_LOCK = threading.Lock()


def get_current_user():
    """从请求头 Authorization: Bearer <token> 解析出当前用户，失败返回 None"""
    auth = request.headers.get("Authorization")
    if not auth or not auth.startswith("Bearer "):
        return None
    token = auth[7:]
    try:
        payload = jwt.decode(token, app.config["SECRET_KEY"], algorithms=["HS256"])
        user = db.session.get(User, payload.get("user_id"))
        return user
    except Exception:
        return None


def login_required(f):
    @wraps(f)
    def wrapped(*args, **kwargs):
        user = get_current_user()
        if not user:
            return jsonify({"error": "请先登录"}), 401
        return f(*args, **kwargs)
    return wrapped


def admin_required(f):
    @wraps(f)
    def wrapped(*args, **kwargs):
        user = get_current_user()
        if not user:
            return jsonify({"error": "请先登录"}), 401
        if user.role != "admin":
            return jsonify({"error": "需要管理员权限"}), 403
        return f(*args, **kwargs)
    return wrapped


def safe_decode_header(header_raw):
    if not header_raw:
        return ""
    try:
        dh = decode_header(header_raw)
        parts = []
        for content, encoding in dh:
            if isinstance(content, bytes):
                enc = encoding if encoding and "unknown" not in (encoding or "").lower() else "gb18030"
                try:
                    parts.append(content.decode(enc))
                except Exception:
                    parts.append(content.decode("utf-8", errors="ignore"))
            else:
                parts.append(str(content))
        return "".join(parts)
    except Exception:
        return str(header_raw)


@app.route("/")
def home():
    index_path = os.path.join(app.static_folder, "index.html")
    if os.path.exists(index_path):
        return send_file(index_path)
    return send_file("index.html")


def update_task(tid, **kwargs):
    with TASKS_LOCK:
        if tid in TASKS:
            TASKS[tid].update(kwargs)


def run_mail_pipeline(tid, acc, pw, months):
    """
    QQ 邮箱稳定版：
    - 不依赖 IMAP SINCE
    - 不使用 break
    - 手动严格日期过滤
    - 兼容各种邮件时间格式
    """

    try:
        update_task(tid, status_text="正在建立加密连接 (IMAP SSL)...")

        imap = imaplib.IMAP4_SSL("imap.qq.com")
        imap.login(acc, pw)
        imap.select("INBOX")

        # ----------------------------
        # 1️⃣ 计算时间范围
        # ----------------------------
        today = datetime.date.today()

        if not isinstance(months, int) or months <= 0:
            months = 1

        target_date = today - relativedelta(months=months)

        print(f"[邮件拉取] 拉取范围: {target_date} ~ {today} ({months} 个月)")

        # ----------------------------
        # 2️⃣ 获取全部邮件 ID
        # （QQ IMAP 不可靠，不能用 SINCE）
        # ----------------------------
        status, data = imap.search(None, "ALL")
        if status != "OK":
            raise Exception("IMAP 搜索失败")

        all_ids = data[0].split()

        print(f"[邮件拉取] 邮箱总邮件数: {len(all_ids)}")

        update_task(tid, status_text="正在筛选发票邮件...")

        # ----------------------------
        # 3️⃣ 手动过滤
        # ----------------------------
        final_ids = []

        keywords = ["发票", "开票", "电子票", "专用发票", "普通发票"]

        for m_id in all_ids:
            try:
                _, head_data = imap.fetch(
                    m_id,
                    "(BODY[HEADER.FIELDS (SUBJECT DATE)])"
                )

                if not head_data or not head_data[0]:
                    continue

                msg = email.message_from_bytes(head_data[0][1])

                subject = safe_decode_header(msg.get("Subject", ""))
                date_str = msg.get("Date", "")

                # ----------------------------
                # 日期解析
                # ----------------------------
                try:
                    msg_date = parsedate_to_datetime(date_str)

                    # 转为本地日期
                    if msg_date.tzinfo is not None:
                        msg_date = msg_date.astimezone().replace(tzinfo=None)

                    msg_date_only = msg_date.date()

                except Exception:
                    # 日期解析失败直接跳过
                    continue

                # ----------------------------
                # 时间范围过滤
                # ----------------------------
                if not (target_date <= msg_date_only <= today):
                    continue

                # ----------------------------
                # 关键词过滤
                # ----------------------------
                if not any(k in subject for k in keywords):
                    continue

                final_ids.append(m_id)

            except Exception:
                continue

        total = len(final_ids)

        print(f"[邮件拉取] 符合条件的发票邮件: {total} 封")

        update_task(
            tid,
            total=total,
            status_text=f"发现 {total} 封发票邮件，开始处理附件..."
        )

        if total == 0:
            update_task(
                tid,
                status="done",
                status_text="未找到符合条件的发票邮件",
                rows=[],
                origin_paths=[]
            )
            imap.logout()
            return

        # ----------------------------
        # 4️⃣ 下载附件并解析
        # ----------------------------
        rows = []
        paths = []

        save_path = os.path.join(ORIGIN_DIR, tid)
        os.makedirs(save_path, exist_ok=True)

        for i, m_id in enumerate(final_ids):
            try:
                _, mdata = imap.fetch(m_id, "(RFC822)")
                if not mdata or not mdata[0]:
                    continue

                msg = email.message_from_bytes(mdata[0][1])

                attachment_count = 0

                for part in msg.walk():
                    fname = part.get_filename()

                    if fname and fname.lower().endswith(
                        (".pdf", ".jpg", ".png", ".jpeg")
                    ):
                        f_dec = safe_decode_header(fname)
                        local_p = os.path.join(
                            save_path,
                            f"{len(paths)}_{f_dec}"
                        )

                        with open(local_p, "wb") as f:
                            f.write(part.get_payload(decode=True))

                        preview_path = os.path.join(
                            PREVIEW_DIR,
                            f"{tid}_{len(rows)}.jpg"
                        )

                        content, _ = parse_invoice_with_qwen(
                            local_p,
                            save_preview_to=preview_path
                        )

                        rows.append(
                            parse_invoice_result_to_row(content)
                        )

                        paths.append(local_p)
                        attachment_count += 1

                if attachment_count > 0:
                    print(f"✅ 邮件 {m_id.decode()} 提取 {attachment_count} 个附件")

                update_task(
                    tid,
                    current=i + 1,
                    progress=int(((i + 1) / total) * 100),
                    rows=list(rows),
                    origin_paths=list(paths)
                )

            except Exception:
                continue

        # ----------------------------
        # 5️⃣ 生成 Excel
        # ----------------------------
        excel_key = str(uuid.uuid4())
        build_excel(rows, os.path.join(EXCEL_DIR, f"{excel_key}.xlsx"))

        update_task(
            tid,
            status="done",
            excel_key=excel_key,
            status_text=f"同步完成！共解析 {len(rows)} 个附件"
        )

        with app.app_context():
            rec = InvoiceRecord.query.filter_by(task_id=tid).first()
            if rec:
                rec.status = "done"
                rec.file_count = len(rows)
                rec.excel_key = excel_key
                db.session.commit()

        imap.logout()

    except Exception as e:
        print(f"[邮件拉取] 执行出错: {str(e)}")

        update_task(
            tid,
            status="error",
            status_text=f"执行出错: {str(e)}"
        )

        with app.app_context():
            rec = InvoiceRecord.query.filter_by(task_id=tid).first()
            if rec:
                rec.status = "error"
                db.session.commit()
@app.route("/api/auth/register", methods=["POST"])
def register():
    data = request.get_json() or {}
    username = (data.get("username") or "").strip()
    password = data.get("password") or ""
    email_str = (data.get("email") or "").strip()
    if not username or not password or not email_str:
        return jsonify({"error": "用户名、邮箱、密码不能为空"}), 400
    if User.query.filter_by(username=username).first():
        return jsonify({"error": "用户名已存在"}), 400
    if User.query.filter_by(email=email_str).first():
        return jsonify({"error": "邮箱已被注册"}), 400
    user = User(username=username, email=email_str)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    token = jwt.encode(
        {"user_id": user.id},
        app.config["SECRET_KEY"],
        algorithm="HS256",
    )
    return jsonify({"token": token, "user": user.to_dict()})


@app.route("/api/auth/login", methods=["POST"])
def login():
    data = request.get_json() or {}
    username = (data.get("username") or "").strip()
    password = data.get("password") or ""
    if not username or not password:
        return jsonify({"error": "用户名和密码不能为空"}), 400
    user = User.query.filter_by(username=username).first()
    if not user or not user.check_password(password):
        return jsonify({"error": "用户名或密码错误"}), 401
    token = jwt.encode(
        {"user_id": user.id},
        app.config["SECRET_KEY"],
        algorithm="HS256",
    )
    return jsonify({"token": token, "user": user.to_dict()})


@app.route("/api/auth/me")
@login_required
def auth_me():
    user = get_current_user()
    return jsonify(user.to_dict())


@app.route("/api/parse-upload", methods=["POST"])
@login_required
def upload_api():
    user = get_current_user()
    files = request.files.getlist("file")
    if not files:
        return jsonify({"error": "请选择至少一个文件"}), 400
    tid = str(uuid.uuid4())
    TASKS[tid] = {
        "status": "running",
        "status_text": "上传成功，启动识别...",
        "rows": [],
        "origin_paths": [],
        "current": 0,
        "total": len(files),
        "progress": 0,
        "user_id": user.id,
    }
    rec = InvoiceRecord(user_id=user.id, task_id=tid, source="upload", file_count=len(files), status="running")
    db.session.add(rec)
    db.session.commit()

    # 关键修复：必须在请求结束前把上传文件落盘；否则后台线程读取时流已关闭，会报 I/O operation on closed file
    save_dir = os.path.join(ORIGIN_DIR, tid)
    os.makedirs(save_dir, exist_ok=True)
    saved_paths = []
    try:
        for i, f in enumerate(files):
            name = secure_filename(f.filename or "") or f"file_{i}"
            p = os.path.join(save_dir, f"{i}_{name}")
            f.save(p)
            saved_paths.append(p)
        update_task(tid, origin_paths=list(saved_paths))
    except Exception as e:
        update_task(tid, status="error", status_text=f"保存上传文件失败: {str(e)}")
        with app.app_context():
            r = InvoiceRecord.query.filter_by(task_id=tid).first()
            if r:
                r.status = "error"
                db.session.commit()
        return jsonify({"error": "保存上传文件失败"}), 500

    def worker(paths_on_disk):
        paths, rows = [], []
        total = len(paths_on_disk) or 1
        try:
            for i, p in enumerate(paths_on_disk):
                paths.append(p)
                p_path = os.path.join(PREVIEW_DIR, f"{tid}_{i}.jpg")
                content, _ = parse_invoice_with_qwen(p, save_preview_to=p_path)
                rows.append(parse_invoice_result_to_row(content))
                update_task(
                    tid,
                    current=i + 1,
                    progress=int(((i + 1) / total) * 100),
                    rows=list(rows),
                    origin_paths=list(paths),
                )
            excel_key = str(uuid.uuid4())
            build_excel(rows, os.path.join(EXCEL_DIR, f"{excel_key}.xlsx"))
            update_task(tid, status="done", excel_key=excel_key, status_text="解析完成！")
            with app.app_context():
                r = InvoiceRecord.query.filter_by(task_id=tid).first()
                if r:
                    r.status = "done"
                    r.file_count = len(rows)
                    r.excel_key = excel_key
                    db.session.commit()
        except Exception as e:
            update_task(tid, status="error", status_text=f"执行出错: {str(e)}")
            with app.app_context():
                r = InvoiceRecord.query.filter_by(task_id=tid).first()
                if r:
                    r.status = "error"
                    db.session.commit()

    threading.Thread(target=worker, args=(list(saved_paths),)).start()
    return jsonify({"task_id": tid})


@app.route("/api/parse-from-email", methods=["POST"])
@login_required
def email_api():
    user = get_current_user()
    d = request.json or {}
    
    # ✅ 验证参数
    months = d.get("months", 1)  # 改成默认 1 个月
    if not isinstance(months, int) or months <= 0:
        months = 1
    
    tid = str(uuid.uuid4())
    TASKS[tid] = {
        "status": "running",
        "status_text": "初始化...",
        "rows": [],
        "origin_paths": [],
        "current": 0,
        "total": 0,
        "progress": 0,
        "user_id": user.id,
    }
    rec = InvoiceRecord(user_id=user.id, task_id=tid, source="email", file_count=0, status="running")
    db.session.add(rec)
    db.session.commit()
    
    print(f"[邮件API] 启动拉取任务: months={months}")
    threading.Thread(target=run_mail_pipeline, args=(tid, d["email"], d["auth_code"], months)).start()
    return jsonify({"task_id": tid})


def _task_for_user(tid):
    with TASKS_LOCK:
        t = TASKS.get(tid)
    if not t:
        return None
    uid = t.get("user_id")
    cur = get_current_user()
    if not cur:
        return None
    if cur.role == "admin":
        return t
    if uid != cur.id:
        return None
    return t


@app.route("/api/task/<tid>")
@login_required
def get_task(tid):
    t = _task_for_user(tid)
    if not t:
        return jsonify({"error": "任务不存在或无权访问"}), 404
    out = dict(t)
    out.pop("user_id", None)
    return jsonify(out)


@app.route("/api/preview/<tid>/<int:idx>")
@login_required
def get_preview(tid, idx):
    if not _task_for_user(tid):
        return "Forbidden", 403
    p = os.path.join(PREVIEW_DIR, f"{tid}_{idx}.jpg")
    return send_file(p) if os.path.exists(p) else ("Wait...", 404)


@app.route("/api/download-excel/<key>")
@login_required
def dl_excel(key):
    cur = get_current_user()
    path = os.path.join(EXCEL_DIR, f"{key}.xlsx")
    if not os.path.exists(path):
        return jsonify({"error": "文件不存在"}), 404
    if cur.role != "admin":
        rec = InvoiceRecord.query.filter_by(excel_key=key).first()
        if not rec or rec.user_id != cur.id:
            return jsonify({"error": "无权下载"}), 403
    return send_file(path, as_attachment=True)


@app.route("/api/admin/users")
@admin_required
def admin_users():
    users = User.query.order_by(User.id.desc()).all()
    return jsonify([u.to_dict() for u in users])


@app.route("/api/admin/stats")
@admin_required
def admin_stats():
    today_start = datetime.datetime.combine(datetime.date.today(), datetime.datetime.min.time())
    user_count = User.query.count()
    record_count = InvoiceRecord.query.count()
    today_count = InvoiceRecord.query.filter(InvoiceRecord.created_at >= today_start).count()
    return jsonify({"user_count": user_count, "record_count": record_count, "today_count": today_count})


@app.route("/api/admin/records")
@admin_required
def admin_records():
    page = max(1, request.args.get("page", 1, type=int))
    per_page = min(50, max(1, request.args.get("per_page", 20, type=int)))
    q = InvoiceRecord.query.order_by(InvoiceRecord.id.desc())
    total = q.count()
    items = q.offset((page - 1) * per_page).limit(per_page).all()
    return jsonify({"total": total, "items": [r.to_dict() for r in items]})


def init_db():
    with app.app_context():
        db.create_all()
        if User.query.filter_by(username="admin").first() is None:
            admin = User(username="admin", email="admin@local.dev", role="admin")
            admin.set_password("admin123")
            db.session.add(admin)
            db.session.commit()
            print("Created default admin: admin / admin123")


if __name__ == "__main__":
    init_db()
    app.run(port=5000, debug=True)