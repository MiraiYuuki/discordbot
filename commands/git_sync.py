import loader
import auth
import sys
import os
import hashlib
import sh
import config

class DirectorySnapshot(object):
    def __init__(self, from_):
        self.root = from_
        self.snapshot = {}
        self.make_snapshot(from_)

    def make_snapshot(self, fromdir):
        for name in os.listdir(fromdir):
            fp = os.path.join(fromdir, name)

            if os.path.isdir(fp):
                continue

            hash = hashlib.sha256()
            with open(fp, "rb") as srcfile:
                hash.update(srcfile.read())

            self.snapshot[name] = hash.hexdigest()

    def has_file_changed(self, filename):
        fp = os.path.join(self.root, filename)

        hash = hashlib.sha256()
        with open(fp, "rb") as srcfile:
            hash.update(srcfile.read())

        if hash.hexdigest() != self.snapshot[filename]:
            return 1
        else:
            return 0

P_SELF_UPDATE = auth.declare_right("SELF_UPDATE")
ESSENTIAL_FILES = ["auth.py", "bot.py", "command_object.py", "config.py", "error_reporting.py",
    "loader.py"]

@loader.command("sync",
    description="Update from a configured git repository.")
@auth.requires_right(P_SELF_UPDATE)
async def sync_command(context, message, content):
    if not content:
        content = config.get("git_sync.default_pull_args", "origin master")

    code_dir = os.path.dirname(sys.modules["__main__"].__file__)
    ds = DirectorySnapshot(code_dir)

    git = sh.git.bake("--git-dir=" + os.path.join(code_dir, ".git"),
        "--work-tree=" + code_dir)

    cur_rev = "".join(git("rev-list", "HEAD", "-n", "1", _iter=1)).strip()

    git.fetch(*content.split())
    git.reset("--hard", "/".join(content.split()))

    new_rev = "".join(git("rev-list", "HEAD", "-n", "1", _iter=1)).strip()

    need_to_restart = 0
    for name in ESSENTIAL_FILES:
        if ds.has_file_changed(name):
            need_to_restart = 1

    if ds.has_file_changed("requirements.txt"):
        sh.pip3.install("-r", os.path.join(code_dir, "requirements.txt"))
        need_to_restart = 1

    await context.reply("Update complete. HEAD moved from {0} to {1}.".format(
        cur_rev, new_rev))

    if need_to_restart:
        await context.reply("Additionally, a core file was modified. Restarting...")
        context.of("discordbot").restart()
