#!/usr/bin/env python3
"""Host and manage Economy Simulator with Docker Compose. Standard library only.

  python3 ecs.py            guided setup + start (run this first)
  python3 ecs.py setup      create .env (address, owner password, generated secrets)
  python3 ecs.py start      build and start the site   (--https for automatic HTTPS)
  python3 ecs.py stop       stop the site (data is kept)
  python3 ecs.py status     show containers and check the site responds
  python3 ecs.py logs [svc] follow logs (web, frontend, db, ...)
  python3 ecs.py invite     print a one-time signup link for a new user
  python3 ecs.py backup     dump the database to backup-<date>.sql
  python3 ecs.py update     git pull, then rebuild and restart
  python3 ecs.py doctor     check that Docker etc. are ready
"""
import argparse
import getpass
import os
import re
import secrets
import shutil
import subprocess
import sys
import time
import urllib.request
import uuid
from datetime import datetime

ROOT = os.path.dirname(os.path.abspath(__file__))
ENV_FILE = os.path.join(ROOT, ".env")
ENV_EXAMPLE = os.path.join(ROOT, ".env.example")


def die(msg):
    print(f"error: {msg}", file=sys.stderr)
    sys.exit(1)


def run(cmd, check=True, capture=False, input_text=None):
    return subprocess.run(
        cmd, cwd=ROOT, check=check, text=True, input=input_text,
        stdout=subprocess.PIPE if capture else None,
        stderr=subprocess.STDOUT if capture else None,
    )


# ---------- .env handling ----------

def read_env():
    values = {}
    if os.path.exists(ENV_FILE):
        with open(ENV_FILE) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    values[k] = v
    return values


def write_env(updates):
    """Update keys in .env, keeping comments and order."""
    if not os.path.exists(ENV_FILE):
        shutil.copy(ENV_EXAMPLE, ENV_FILE)
    with open(ENV_FILE) as f:
        lines = f.read().splitlines()
    seen = set()
    for i, line in enumerate(lines):
        m = re.match(r"^([A-Z_]+)=", line)
        if m and m.group(1) in updates:
            lines[i] = f"{m.group(1)}={updates[m.group(1)]}"
            seen.add(m.group(1))
    for k, v in updates.items():
        if k not in seen:
            lines.append(f"{k}={v}")
    with open(ENV_FILE, "w") as f:
        f.write("\n".join(lines) + "\n")
    try:
        os.chmod(ENV_FILE, 0o600)
    except OSError:
        pass


# ---------- checks ----------

def docker_problem():
    if not shutil.which("docker"):
        return "Docker is not installed. Install it from https://docs.docker.com/engine/install/ and run this again."
    r = run(["docker", "compose", "version"], check=False, capture=True)
    if r.returncode != 0:
        return "Docker Compose v2 is missing ('docker compose' failed). Update Docker or install the compose plugin."
    r = run(["docker", "info"], check=False, capture=True)
    if r.returncode != 0:
        return "Docker is installed but not running or you lack permission (try 'sudo usermod -aG docker $USER', then log in again)."
    return None


def need_docker():
    problem = docker_problem()
    if problem:
        die(problem)


def compose(*args, https=None, check=True, capture=False, input_text=None):
    if https is None:
        https = os.path.exists(ENV_FILE) and read_env().get("HTTPS_ENABLED") == "1"
    cmd = ["docker", "compose"] + (["--profile", "https"] if https else []) + list(args)
    return run(cmd, check=check, capture=capture, input_text=input_text)


# ---------- commands ----------

def cmd_doctor(_args=None):
    problem = docker_problem()
    print("Docker:", "OK" if not problem else "PROBLEM - " + problem)
    print("Git:   ", "OK" if shutil.which("git") else "not found (only needed for 'update')")
    print(".env:  ", "present" if os.path.exists(ENV_FILE) else "missing (run: python3 ecs.py setup)")
    return 0 if not problem else 1


def ask(prompt, default=None):
    suffix = f" [{default}]" if default else ""
    answer = input(f"{prompt}{suffix}: ").strip()
    return answer or default


def cmd_setup(_args=None):
    if os.path.exists(ENV_FILE):
        die(".env already exists. Edit it directly, or delete it to start over (your data is not deleted).")
    print("\n== Economy Simulator setup ==\n")
    print("What address will people use to reach your site?")
    print("  - testing on this computer:   http://localhost:5000")
    print("  - a real website (HTTPS):     https://yourdomain.com  (its DNS must point at this server)")
    url = ask("Site address", "http://localhost:5000").rstrip("/")
    if not re.match(r"^https?://[^/\s]+$", url):
        die("The address must look like http://localhost:5000 or https://example.com (no path).")
    updates = {"PUBLIC_URL": url}
    if url.startswith("https://"):
        updates["DOMAIN"] = url[len("https://"):]
        updates["HTTPS_ENABLED"] = "1"
        print(f"\nHTTPS: Caddy will get a free certificate for {updates['DOMAIN']}. Ports 80 and 443 must be open.")
    else:
        updates["HTTPS_ENABLED"] = "0"
        if "localhost" not in url and "127.0.0.1" not in url:
            updates["HTTP_BIND"] = "0.0.0.0"
            print("\nPlain HTTP on a non-local address: the site will listen on all interfaces, port 5000.")

    print("\nThe owner account is called ROBLOX. It has the admin panel at /admin.")
    while True:
        pw = getpass.getpass("Choose the owner password (8+ characters): ")
        if len(pw) < 8:
            print("  too short"); continue
        if any(c in pw for c in '"\\$`\n'):
            print('  please avoid the characters  "  \\  $  `'); continue
        if getpass.getpass("Repeat it: ") != pw:
            print("  they didn't match"); continue
        break
    updates.update({
        "OWNER_PASSWORD": pw,
        "POSTGRES_PASSWORD": secrets.token_hex(16),
        "JWT_SECRET": secrets.token_hex(24),
        "CSRF_KEY": secrets.token_hex(32),
        "INTERNAL_AUTH": secrets.token_hex(16),
    })
    write_env(updates)
    print("\nSaved settings to .env (keep that file private and back it up).")
    return 0


def wait_for_site(url_port, timeout=420):
    url = f"http://127.0.0.1:{url_port}/auth/home"
    start = time.time()
    while time.time() - start < timeout:
        try:
            with urllib.request.urlopen(url, timeout=5) as r:
                if r.status < 500:
                    return True
        except urllib.error.HTTPError as e:
            if e.code < 500:
                return True
        except Exception:
            pass
        time.sleep(3)
    return False


def cmd_start(args):
    need_docker()
    if not os.path.exists(ENV_FILE):
        die("No .env yet. Run: python3 ecs.py setup")
    env = read_env()
    if getattr(args, "https", False):
        if not env.get("DOMAIN"):
            die("Set DOMAIN in .env first (or answer setup with an https:// address).")
        write_env({"HTTPS_ENABLED": "1"})
    print("Building and starting (the first build takes several minutes)...")
    compose("up", "-d", "--build")
    port = env.get("HTTP_PORT", "5000")
    print("Waiting for the site to come up...")
    if wait_for_site(port):
        print(f"\nThe site is running: {env['PUBLIC_URL']}")
        print("Log in as ROBLOX with your owner password. Admin panel: /admin")
        print("Add users with:  python3 ecs.py invite")
    else:
        print("\nThe site did not answer in time. Check: python3 ecs.py logs web")
        return 1
    return 0


def cmd_stop(_args=None):
    need_docker()
    compose("down")
    print("Stopped. Your data is kept; start again with: python3 ecs.py start")


def cmd_status(_args=None):
    need_docker()
    compose("ps")
    env = read_env()
    ok = wait_for_site(env.get("HTTP_PORT", "5000"), timeout=5)
    print("\nWebsite responding:", "yes" if ok else "NO")


def cmd_logs(args):
    need_docker()
    try:
        compose("logs", "-f", "--tail=100", *args.service)
    except KeyboardInterrupt:
        pass


def cmd_invite(_args=None):
    need_docker()
    env = read_env()
    invite_id = str(uuid.uuid4())
    r = compose("exec", "-T", "db", "psql", "-U", "ecs", "-d", "ecs", "-q", "-c",
                f"INSERT INTO user_invite (id, author_id) VALUES ('{invite_id}', 1)",
                check=False, capture=True)
    if r.returncode != 0:
        die("Could not create the invite. Is the site running and the database ready?\n" + (r.stdout or ""))
    print(f"{env.get('PUBLIC_URL', '')}/auth/signup?inviteId={invite_id}")
    print("(one-time link: send it to the person you want to join)")


def cmd_backup(_args=None):
    need_docker()
    name = datetime.now().strftime("backup-%Y%m%d-%H%M%S.sql")
    with open(os.path.join(ROOT, name), "w") as f:
        r = subprocess.run(["docker", "compose", "exec", "-T", "db", "pg_dump", "-U", "ecs", "ecs"],
                           cwd=ROOT, stdout=f)
    if r.returncode != 0:
        os.remove(os.path.join(ROOT, name))
        die("Backup failed. Is the site running?")
    print(f"Wrote {name}. Uploaded files live in the Docker volume 'ecs_site-data'.")


def cmd_update(args):
    need_docker()
    run(["git", "pull", "--ff-only"])
    return cmd_start(args)


def cmd_wizard(args):
    problem = docker_problem()
    if problem:
        die(problem)
    if not os.path.exists(ENV_FILE):
        cmd_setup()
    args.https = False
    code = cmd_start(args)
    if code == 0:
        print()
        if (ask("Create a signup link for your first user now? (y/n)", "y") or "").lower().startswith("y"):
            cmd_invite()
    return code


def main():
    p = argparse.ArgumentParser(description="Host Economy Simulator", formatter_class=argparse.RawDescriptionHelpFormatter,
                                epilog=__doc__)
    sub = p.add_subparsers(dest="cmd")
    sub.add_parser("setup")
    s = sub.add_parser("start"); s.add_argument("--https", action="store_true")
    sub.add_parser("stop"); sub.add_parser("status"); sub.add_parser("invite")
    sub.add_parser("backup"); sub.add_parser("doctor")
    s = sub.add_parser("update"); s.add_argument("--https", action="store_true")
    s = sub.add_parser("logs"); s.add_argument("service", nargs="*")
    args = p.parse_args()
    handler = {
        None: cmd_wizard, "setup": cmd_setup, "start": cmd_start, "stop": cmd_stop, "status": cmd_status,
        "logs": cmd_logs, "invite": cmd_invite, "backup": cmd_backup, "update": cmd_update, "doctor": cmd_doctor,
    }[args.cmd]
    try:
        sys.exit(handler(args) or 0)
    except subprocess.CalledProcessError as e:
        die(f"command failed: {' '.join(e.cmd)}")
    except (KeyboardInterrupt, EOFError):
        print("\ncancelled")
        sys.exit(130)


if __name__ == "__main__":
    main()
