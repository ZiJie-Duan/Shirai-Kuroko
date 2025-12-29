#!/usr/bin/env python3
import os
import sys
import argparse
import oss2
from tqdm import tqdm
from pathlib import Path

DEFAULT_PREFIX = "shirai-kuroko/"
DEFAULT_EXPIRES = 86400  # 24小时


def load_env():
    """加载 .env 文件（位于脚本目录的上一级）"""
    script_dir = Path(__file__).resolve().parent
    env_path = script_dir.parent / ".env"
    
    if not env_path.exists():
        print(f"❌ .env 文件不存在: {env_path}")
        sys.exit(1)
    
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                k, v = line.split("=", 1)
                os.environ[k.strip()] = v.strip()


def get_bucket():
    """初始化 OSS bucket"""
    load_env()
    auth = oss2.Auth(
        os.environ["OSS_ACCESS_KEY_ID"],
        os.environ["OSS_ACCESS_KEY_SECRET"],
    )
    return oss2.Bucket(
        auth,
        os.environ["OSS_ENDPOINT"],
        os.environ["OSS_BUCKET_NAME"],
    )


def upload(bucket, local_path, oss_key, expires):
    """上传文件"""
    p = Path(local_path)
    if not p.exists():
        print(f"❌ 本地文件不存在: {local_path}")
        sys.exit(1)

    filename = p.name
    size = p.stat().st_size

    # 上传带进度条
    with tqdm(total=size, unit="B", unit_scale=True, desc=filename) as bar:
        def cb(consumed, total):
            bar.update(consumed - bar.n)
        bucket.put_object_from_file(oss_key, str(p), progress_callback=cb)

    # 生成签名 URL
    url = bucket.sign_url("GET", oss_key, expires)

    # 输出结果
    print()
    print("✅ 上传完成")
    print()
    print(f"Key: {oss_key}")
    print(f"URL ({expires}s):")
    print(url)
    print()
    print(f'wget -O "{filename}" "{url}"')
    print()

    # 上传后交互
    post_upload_prompt(bucket, oss_key)


def post_upload_prompt(bucket, oss_key):
    """上传后的交互：回车退出，d 删除"""
    try:
        choice = input("[回车退出 / d 删除]> ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        print()
        return

    if choice == "d":
        confirm = input("确认删除？(y/N)> ").strip().lower()
        if confirm == "y":
            bucket.delete_object(oss_key)
            print(f"🗑️ 已删除: {oss_key}")
        else:
            print("取消删除")


def delete(bucket, oss_key):
    """删除文件"""
    if not bucket.object_exists(oss_key):
        print(f"⚠️ 对象不存在: {oss_key}")
        sys.exit(1)

    confirm = input(f"确认删除 {oss_key}？(y/N)> ").strip().lower()
    if confirm == "y":
        bucket.delete_object(oss_key)
        print(f"🗑️ 已删除: {oss_key}")
    else:
        print("取消删除")


def main():
    parser = argparse.ArgumentParser(
        description="OSS 文件管理工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  %(prog)s u ./video.mp4                     # 上传，key 自动生成
  %(prog)s u ./video.mp4 my/path/video.mp4   # 上传，指定 key
  %(prog)s u ./video.mp4 --expires 3600      # 上传，签名有效期 1 小时
  %(prog)s d shirai-kuroko/video.mp4         # 删除
        """,
    )

    subparsers = parser.add_subparsers(dest="cmd", required=True)

    # 上传命令
    p_upload = subparsers.add_parser("u", help="上传文件")
    p_upload.add_argument("local_path", help="本地文件路径")
    p_upload.add_argument("oss_key", nargs="?", default=None, help="OSS key（可选，默认使用前缀+文件名）")
    p_upload.add_argument("--expires", type=int, default=DEFAULT_EXPIRES, help=f"签名有效期（秒），默认 {DEFAULT_EXPIRES}")

    # 删除命令
    p_delete = subparsers.add_parser("d", help="删除文件")
    p_delete.add_argument("oss_key", help="OSS key")

    args = parser.parse_args()
    bucket = get_bucket()

    if args.cmd == "u":
        oss_key = args.oss_key
        if not oss_key:
            filename = Path(args.local_path).name
            oss_key = f"{DEFAULT_PREFIX}{filename}"
        upload(bucket, args.local_path, oss_key, args.expires)

    elif args.cmd == "d":
        delete(bucket, args.oss_key)


if __name__ == "__main__":
    main()