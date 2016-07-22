import os
import subprocess

import sys


class GitRepository:
    def __init__(self, path, branch):
        self.branch = branch
        self.path = path

    def _format_git_cmd(self, cmd):
        return "git --git-dir='{}' --work-tree='{}' {}".format(os.path.join(self.path, ".git"), self.path, cmd)

    def _git_get_output(self, cmd):
        return subprocess.check_output(self._format_git_cmd(cmd), shell=True).strip().decode("UTF-8")

    def _git_redirected(self, cmd):
        print(">> git " + cmd)
        return subprocess.call(self._format_git_cmd(cmd), shell=True, stdout=sys.stdout, stderr=sys.stderr,
                               stdin=sys.stdin)

    def _git_redirected_success(self, cmd):
        ret = self._git_redirected(cmd)

        assert ret == 0

    def get_commit(self):
        return self._git_get_output("rev-parse --short {}".format(self.branch)).lower()

    def get_log(self, pattern):
        tags = self._git_get_output("for-each-ref --sort=-taggerdate --format '%(tag)' refs/tags | grep '{}' | head -n2"
                                    .format(pattern)).splitlines()

        return self._git_get_output("log {}^..{}^ --no-merges --stat"
                                    " --pretty=format:"
                                    "\"------------------------------------------------------------------------%n"
                                    "commit %h%nAuthor: %an <%ad>%n"
                                    "Commit: %cn <%cd>%n%n    %s\"".format(tags[1], tags[0]))

    def get_latest_tag_commit(self, pattern):
        tag = self._git_get_output("for-each-ref --sort=-taggerdate --format '%(tag)' refs/tags | grep '{}' | head -n1"
                                   .format(pattern))

        return self._git_get_output("rev-parse --short {}^".format(tag))

    def update_repository(self):
        self._git_redirected_success("checkout '{}'".format(self.branch))
        self._git_redirected_success("pull origin '{}'".format(self.branch))

    def prepare_repo(self):
        self._git_redirected_success("checkout '{}'".format(self.branch))

        has_changes = self._git_redirected("diff-index --quiet HEAD --") != 0

        stashed_changes = False
        if has_changes:
            print("Stashing local changes for later recovery")
            self._git_redirected_success("stash -u -a")
            stashed_changes = True

        # Detach HEAD so we don't change the branch we are on
        self._git_redirected_success("checkout --detach")

        return stashed_changes

    def commit_and_tag(self, tag_name):
        self._git_redirected_success("add .")
        self._git_redirected_success(
            "commit -m 'Automated build commit' --author='SirKnightly <SirKnightlySCP@gmail.com>'")
        self._git_redirected_success("tag -a '{}' -m 'Build script tag'".format(tag_name))
        self._git_redirected_success("push --tags")

    def restore_repo(self, stashed_changes):
        self._git_redirected_success("checkout '{}'".format(self.branch))

        if stashed_changes:
            print("Restoring previous changes")
            self._git_redirected_success("stash pop")
