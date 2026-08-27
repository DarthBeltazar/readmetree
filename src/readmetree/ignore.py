"""Decide which paths are excluded from the scanned tree.

Priority, highest first:
1. `force_include` patterns in the config always win (a path they cover is
   shown even if .gitignore, the untracked-file check, or the
   always-exclude list would hide it).
2. Everything else is excluded if it matches the built-in always-exclude
   list, the config's `exclude:` patterns, or .gitignore (via `git
   check-ignore` when a repo is present, otherwise a `pathspec` fallback).
3. In a git repo, a *file* that isn't tracked by git (i.e. never `git
   add`ed) is excluded too, even if nothing ignores it — the tree is meant
   to reflect what's actually in the repository, not scratch files sitting
   in the working copy. This only applies to files; directories aren't
   tracked by git themselves; an untracked-only directory ends up empty and
   is dropped by the scanner's own empty-directory pruning instead. Outside
   a git repo there's no way to know what "tracked" would mean, so this
   check is skipped and only .gitignore filtering applies.

Ignore checks are meant to run *before* descending into a directory, so a
huge ignored tree (node_modules, a build dir) is never even walked.
"""

from __future__ import annotations

import fnmatch
import subprocess
from pathlib import Path

import pathspec

from .defaults import ALWAYS_EXCLUDE


class IgnoreMatcher:
    def __init__(
        self,
        root: Path,
        extra_exclude: list[str] | None = None,
        force_include: list[str] | None = None,
        verbose: bool = False,
    ) -> None:
        self.root = root
        self.verbose = verbose
        self._force_include = list(force_include or [])
        self._always_spec = pathspec.PathSpec.from_lines(
            "gitignore", ALWAYS_EXCLUDE + list(extra_exclude or [])
        )
        # .exists() rather than .is_dir(): in a git worktree or submodule,
        # .git is a *file* containing "gitdir: ...", not a directory — but
        # git ls-files/check-ignore work the same either way when cwd is
        # set to the repo root. rootfind.find_root() already uses the same
        # .exists() check for consistency.
        self._use_git = (root / ".git").exists() and _git_available()
        self._gitignore_spec: pathspec.PathSpec | None = None
        self._tracked_files: set[str] | None = None
        if self._use_git:
            self._tracked_files = self._git_ls_files()
        else:
            self._gitignore_spec = self._build_pathspec_fallback()

    # -- public API ---------------------------------------------------

    def filter_ignored(self, dir_rel_path: str, names: list[str], is_dir: dict[str, bool]) -> set[str]:
        """Given a directory's entry names, return the subset that should be
        excluded from the scan (files and directories alike).
        """
        candidates = {name: self._join(dir_rel_path, name) for name in names}

        ignored: set[str] = set()

        # built-in + config exclude list, and (git-based or fallback) gitignore
        if self._use_git:
            git_ignored = self._git_check_ignore(
                [
                    p + "/" if is_dir.get(name) else p
                    for name, p in candidates.items()
                ]
            )
        else:
            git_ignored = None

        for name, rel in candidates.items():
            check_path = rel + "/" if is_dir.get(name) else rel
            is_always = self._always_spec.match_file(check_path)
            if self._use_git:
                is_gitignored = check_path in git_ignored if git_ignored else False
            else:
                is_gitignored = bool(
                    self._gitignore_spec and self._gitignore_spec.match_file(check_path)
                )
            is_untracked_file = (
                self._tracked_files is not None
                and not is_dir.get(name)
                and rel not in self._tracked_files
            )
            if (is_always or is_gitignored or is_untracked_file) and not self._is_force_included(rel):
                ignored.add(name)

        return ignored

    def force_include_pattern(self, rel_path: str) -> str | None:
        """Return the matching force_include pattern for `rel_path`, if any."""
        for pattern in self._force_include:
            check_path = rel_path + "/" if pattern.endswith("/") else rel_path
            if fnmatch.fnmatch(check_path, pattern) or fnmatch.fnmatch(rel_path, pattern.rstrip("/")):
                return pattern
        return None

    def _is_force_included(self, rel_path: str) -> bool:
        return self.force_include_pattern(rel_path) is not None

    # -- internals ------------------------------------------------------

    def _join(self, dir_rel_path: str, name: str) -> str:
        return f"{dir_rel_path}/{name}" if dir_rel_path else name

    def _git_check_ignore(self, rel_paths: list[str]) -> set[str]:
        if not rel_paths:
            return set()
        try:
            proc = subprocess.run(
                ["git", "check-ignore", "--stdin", "-z"],
                cwd=self.root,
                input="\0".join(rel_paths).encode("utf-8"),
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
            )
        except OSError:
            return set()
        out = proc.stdout.decode("utf-8", errors="replace")
        return {p for p in out.split("\0") if p}

    def _git_ls_files(self) -> set[str]:
        """Files git actually tracks (staged or committed) — the set an
        untracked working-copy file needs to join before it shows up in
        the tree.
        """
        try:
            proc = subprocess.run(
                ["git", "ls-files", "-z"],
                cwd=self.root,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
            )
        except OSError:
            return set()
        out = proc.stdout.decode("utf-8", errors="replace")
        return {p for p in out.split("\0") if p}

    def _build_pathspec_fallback(self) -> pathspec.PathSpec:
        """Merge the root .gitignore with any nested .gitignore files found
        in the tree (patterns prefixed by their containing directory). This
        is a best-effort approximation of git's own nested-gitignore
        semantics, used only when no .git directory is available.
        """
        prefixed_lines: list[str] = []
        skip_dirs = {".git", "node_modules", ".venv", "venv"}
        for dirpath, dirnames, filenames in _walk(self.root, skip_dirs):
            dirnames[:] = [d for d in dirnames if d not in skip_dirs]
            if ".gitignore" not in filenames:
                continue
            gitignore_path = Path(dirpath) / ".gitignore"
            rel_dir = Path(dirpath).relative_to(self.root).as_posix()
            prefix = "" if rel_dir == "." else rel_dir + "/"
            try:
                lines = gitignore_path.read_text(encoding="utf-8").splitlines()
            except OSError:
                continue
            for line in lines:
                stripped = line.strip()
                if not stripped or stripped.startswith("#"):
                    continue
                negate = stripped.startswith("!")
                pattern = stripped[1:] if negate else stripped
                anchored = pattern.startswith("/")
                pattern = pattern.lstrip("/")
                new_pattern = prefix + pattern if not anchored else prefix + pattern
                prefixed_lines.append(("!" if negate else "") + new_pattern)
        return pathspec.PathSpec.from_lines("gitignore", prefixed_lines)


def _walk(root: Path, skip_dirs: set[str]):
    import os

    for dirpath, dirnames, filenames in os.walk(root):
        yield dirpath, dirnames, filenames


def _git_available() -> bool:
    try:
        subprocess.run(
            ["git", "--version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
        return True
    except OSError:
        return False
