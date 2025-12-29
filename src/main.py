
import os
import sys
import oss2
from tqdm import tqdm
from pathlib import Path

DEFAULT_PREFIX = "shirai-kuroko/"

# =========================
# 1. 读取 .env
# =========================
def load_env(path=".env"):
    if not os.path.exists(path):
        print(f"❌ .env 文件不存在: {path}")
        sys.exit(1)

    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            k, v = line.split("=", 1)
            os.environ[k.strip()] = v.strip()


load_env()

auth = oss2.Auth(
    os.environ["OSS_ACCESS_KEY_ID"],
    os.environ["OSS_ACCESS_KEY_SECRET"],
)
bucket = oss2.Bucket(
    auth,
    os.environ["OSS_ENDPOINT"],
    os.environ["OSS_BUCKET_NAME"],
)

SIGN_EXPIRES = int(os.environ.get("OSS_SIGN_EXPIRES", "86400"))

# =========================
# 2. 功能函数
# =========================
def upload(local_path, oss_key):
    p = Path(local_path)
    if not p.exists():
        print("❌ 本地文件不存在")
        return

    size = p.stat().st_size
    with tqdm(total=size, unit="B", unit_scale=True, desc=p.name) as bar:

        def cb(consumed, total):
            bar.update(consumed - bar.n)

        bucket.put_object_from_file(
            oss_key,
            str(p),
            progress_callback=cb,
        )

    url = bucket.sign_url("GET", oss_key, SIGN_EXPIRES)
    print("\n✅ 上传完成")
    print(f"Key: {oss_key}")
    print(f"URL ({SIGN_EXPIRES}s):\n{url}\n")


def delete(oss_key):
    if not bucket.object_exists(oss_key):
        print("⚠️ 对象不存在")
        return

    bucket.delete_object(oss_key)
    print(f"🗑️ 已删除: {oss_key}")


# =========================
# 3. CLI
# =========================
HELP = """
指令:
  u  上传文件
  d  删除文件
  h  帮助
  q  退出
"""

print("OSS CLI (u/d/h/q)")
print(HELP)

while True:
    cmd = input("oss> ").strip().lower()

    if cmd == "q":
        break

    elif cmd == "u":
        lp = input("local path: ").strip()
        key = input("oss key   (回车=使用文件名): ").strip()

        if not lp:
            print("❌ local path 不能为空")
            continue

        if not key:
            filename = Path(lp).name
            key = f"{DEFAULT_PREFIX}{filename}"

        upload(lp, key)

    elif cmd == "d":
        key = input("oss key: ").strip()
        delete(key)

    elif cmd == "h":
        print(HELP)

    else:
        print("未知指令，输入 h 查看帮助")