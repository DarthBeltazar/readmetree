"""Load, save, and diff `.readmetree.yml`.

The file is round-tripped through ruamel.yaml with a fixed top-level key
order (version, exclude, force_include, collapse_siblings, entries) and
`entries` written in the same order the tree was scanned (directories then
files, alphabetically) — this is what makes repeated `generate` runs with no
filesystem changes produce a byte-identical file.
"""

from __future__ import annotations

import io
from dataclasses import dataclass, field
from pathlib import Path

from ruamel.yaml import YAML

from .defaults import CONFIG_VERSION

_yaml = YAML(typ="rt")
_yaml.indent(mapping=2, sequence=4, offset=2)
_yaml.width = 4096  # don't line-wrap long descriptions
_yaml.preserve_quotes = True


@dataclass
class ForceIncludeSpec:
    pattern: str
    # Default True: a force_include entry almost always exists to show an
    # otherwise-.gitignore'd *directory* as one line. collapse=False only
    # rescues the directory's own tree line — its children are still
    # filtered by the same .gitignore pattern (gitignore matches on a
    # directory implicitly cover everything under it), so they'd need their
    # own force_include entries too. That's rarely what anyone wants.
    collapse: bool = True


@dataclass
class CollapseSiblingSpec:
    pattern: str
    display: str
    description: str | None = None


@dataclass
class ConfigEntry:
    description: str | None = None
    ignore: bool = False
    pair_with: str | None = None


@dataclass
class ProjectConfig:
    version: int = CONFIG_VERSION
    exclude: list[str] = field(default_factory=list)
    force_include: list[ForceIncludeSpec] = field(default_factory=list)
    collapse_siblings: list[CollapseSiblingSpec] = field(default_factory=list)
    entries: dict[str, ConfigEntry] = field(default_factory=dict)

    # -- loading / saving ------------------------------------------------

    @classmethod
    def load(cls, path: Path) -> "ProjectConfig":
        if not path.exists():
            return cls()
        with path.open("r", encoding="utf-8") as f:
            data = _yaml.load(f) or {}
        return cls(
            version=int(data.get("version", CONFIG_VERSION)),
            exclude=list(data.get("exclude") or []),
            force_include=[
                ForceIncludeSpec(pattern=i["pattern"], collapse=bool(i.get("collapse", False)))
                for i in (data.get("force_include") or [])
            ],
            collapse_siblings=[
                CollapseSiblingSpec(
                    pattern=i["pattern"],
                    display=i.get("display", i["pattern"]),
                    description=i.get("description"),
                )
                for i in (data.get("collapse_siblings") or [])
            ],
            entries={
                key: ConfigEntry(
                    description=val.get("description") if val else None,
                    ignore=bool(val.get("ignore", False)) if val else False,
                    pair_with=val.get("pair_with") if val else None,
                )
                for key, val in (data.get("entries") or {}).items()
            },
        )

    def to_yaml_string(self, entry_order: list[str] | None = None) -> str:
        """Serialize to the exact text `save()` would write, without
        touching disk — lets `generate --check` compare against the
        existing file's bytes.
        """
        ordered_keys = list(entry_order or [])
        remaining = [k for k in self.entries if k not in ordered_keys]
        ordered_keys += remaining

        doc: dict = {
            "version": self.version,
            "exclude": list(self.exclude),
            "force_include": [
                {"pattern": s.pattern, "collapse": s.collapse} for s in self.force_include
            ],
            "collapse_siblings": [
                {"pattern": s.pattern, "display": s.display, "description": s.description}
                for s in self.collapse_siblings
            ],
            "entries": {
                key: _entry_to_dict(self.entries[key])
                for key in ordered_keys
                if key in self.entries
            },
        }

        buf = io.StringIO()
        _yaml.dump(doc, buf)
        return buf.getvalue()

    def save(self, path: Path, entry_order: list[str] | None = None) -> None:
        """Write the config atomically. `entry_order` (a list of config
        keys) controls the order entries are serialized in; keys not listed
        are appended afterwards in their existing order.
        """
        content = self.to_yaml_string(entry_order)
        tmp_path = path.with_suffix(path.suffix + ".tmp")
        with tmp_path.open("w", encoding="utf-8", newline="\n") as f:
            f.write(content)
        tmp_path.replace(path)

    # -- entry helpers ----------------------------------------------------

    def get_description(self, config_key: str) -> str | None:
        entry = self.entries.get(config_key)
        return entry.description if entry else None

    def has_entry(self, config_key: str) -> bool:
        entry = self.entries.get(config_key)
        return entry is not None and entry.description is not None

    def set_description(self, config_key: str, description: str) -> None:
        entry = self.entries.setdefault(config_key, ConfigEntry())
        entry.description = description

    def set_pair_with(self, config_key: str, secondary_path: str) -> None:
        entry = self.entries.setdefault(config_key, ConfigEntry())
        entry.pair_with = secondary_path

    def is_manually_ignored(self, config_key: str) -> bool:
        entry = self.entries.get(config_key)
        return bool(entry and entry.ignore)


def _entry_to_dict(entry: ConfigEntry) -> dict:
    d: dict = {"description": entry.description}
    if entry.ignore:
        d["ignore"] = True
    if entry.pair_with:
        d["pair_with"] = entry.pair_with
    return d


@dataclass
class DiffResult:
    new: list[str]
    removed: list[str]
    kept: list[str]


def diff_entries(scanned_keys: list[str], config: ProjectConfig) -> DiffResult:
    """Compare the freshly scanned config keys against the saved config.

    Keys the user marked `ignore: true` are treated as if they were never
    scanned, so they don't show up as "removed" — they're excluded on
    purpose, not gone from disk.
    """
    effective_scanned = [
        k for k in scanned_keys if not config.is_manually_ignored(k)
    ]
    scanned_set = set(effective_scanned)
    known_keys = {
        k
        for k, e in config.entries.items()
        if e.description is not None and not e.ignore
    }

    new = [k for k in effective_scanned if k not in known_keys]
    removed = sorted(known_keys - scanned_set)
    kept = [k for k in effective_scanned if k in known_keys]
    return DiffResult(new=new, removed=removed, kept=kept)
