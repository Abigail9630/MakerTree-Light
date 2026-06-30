"""File-based node store for MakerTree Library — Rain, Trunk/SOPs, Projects, Archive."""

from __future__ import annotations

import csv
import io
import json
import uuid
from dataclasses import asdict, dataclass, field
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Optional


BRANCHES: dict[str, str] = {
    "rain": "Rain — Brain Dumps",
    "trunk": "Trunk / SOPs",
    "projects": "Projects & Active Work",
    "archive": "Archive / Done",
}

NODE_TYPES: dict[str, str] = {
    "rain_capture": "Rain capture",
    "rain_day": "Rain day folder",
    "sop": "SOP / process",
    "project": "Project",
    "note": "Note",
    "folder": "Folder",
}

CSV_COLUMNS = [
    "id",
    "title",
    "text",
    "branch",
    "node_type",
    "parent_id",
    "project_id",
    "tags",
    "created_at",
    "updated_at",
    "collapsed",
    "sort_order",
]


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _parse_iso(value: str) -> datetime:
    if not value:
        return datetime.min.replace(tzinfo=timezone.utc)
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return datetime.min.replace(tzinfo=timezone.utc)


def _new_id(prefix: str = "node") -> str:
    return f"{prefix}-{uuid.uuid4().hex[:12]}"


@dataclass
class TreeNode:
    id: str
    title: str = ""
    text: str = ""
    branch: str = "rain"
    node_type: str = "note"
    parent_id: Optional[str] = None
    project_id: Optional[str] = None
    tags: list[str] = field(default_factory=list)
    created_at: str = field(default_factory=_utc_now_iso)
    updated_at: str = field(default_factory=_utc_now_iso)
    collapsed: bool = False
    sort_order: int = 0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TreeNode":
        tags = data.get("tags") or []
        if isinstance(tags, str):
            tags = [t.strip() for t in tags.split(",") if t.strip()]
        return cls(
            id=str(data["id"]),
            title=str(data.get("title") or ""),
            text=str(data.get("text") or ""),
            branch=str(data.get("branch") or "rain"),
            node_type=str(data.get("node_type") or "note"),
            parent_id=data.get("parent_id") or None,
            project_id=data.get("project_id") or None,
            tags=list(tags),
            created_at=str(data.get("created_at") or _utc_now_iso()),
            updated_at=str(data.get("updated_at") or _utc_now_iso()),
            collapsed=bool(data.get("collapsed", False)),
            sort_order=int(data.get("sort_order") or 0),
        )


class MakerTreeStore:
    """JSONL-backed store — one object per line, easy to copy/sync via USB or LocalSend."""

    def __init__(self, data_dir: Optional[Path] = None) -> None:
        if data_dir is None:
            data_dir = Path.home() / ".maker_tree" / "library"
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.nodes_path = self.data_dir / "nodes.jsonl"
        self.meta_path = self.data_dir / "meta.json"
        self._nodes: dict[str, TreeNode] = {}
        self._mtime: float = 0.0
        self._load()

    def reload_if_changed(self) -> None:
        if not self.nodes_path.exists():
            return
        mtime = self.nodes_path.stat().st_mtime
        if mtime != self._mtime:
            self._load()

    def _load(self) -> None:
        self._nodes = {}
        if self.nodes_path.exists():
            with self.nodes_path.open(encoding="utf-8") as fh:
                for line in fh:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        node = TreeNode.from_dict(json.loads(line))
                        self._nodes[node.id] = node
                    except (json.JSONDecodeError, KeyError):
                        continue
            self._mtime = self.nodes_path.stat().st_mtime
        else:
            self._mtime = 0.0
        self._write_meta()

    def _persist(self) -> None:
        tmp = self.nodes_path.with_suffix(".jsonl.tmp")
        with tmp.open("w", encoding="utf-8") as fh:
            for node in sorted(self._nodes.values(), key=lambda n: (n.branch, n.sort_order, n.created_at)):
                fh.write(json.dumps(node.to_dict(), ensure_ascii=False) + "\n")
        tmp.replace(self.nodes_path)
        self._mtime = self.nodes_path.stat().st_mtime
        self._write_meta()

    def _write_meta(self) -> None:
        meta = {
            "version": 1,
            "node_count": len(self._nodes),
            "updated_at": _utc_now_iso(),
        }
        self.meta_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")

    @property
    def node_count(self) -> int:
        return len(self._nodes)

    def get(self, node_id: str) -> Optional[TreeNode]:
        return self._nodes.get(node_id)

    def all_nodes(self) -> list[TreeNode]:
        return list(self._nodes.values())

    def list_projects(self) -> list[TreeNode]:
        return sorted(
            [n for n in self._nodes.values() if n.branch == "projects" and n.node_type == "project"],
            key=lambda n: n.title.lower(),
        )

    def list_children(
        self,
        parent_id: Optional[str],
        *,
        branch: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[TreeNode]:
        items = [
            n
            for n in self._nodes.values()
            if n.parent_id == parent_id and (branch is None or n.branch == branch)
        ]
        items.sort(key=lambda n: (-_parse_iso(n.created_at).timestamp(), n.sort_order, n.title.lower()))
        return items[offset : offset + limit]

    def count_children(self, parent_id: Optional[str], *, branch: Optional[str] = None) -> int:
        return sum(
            1
            for n in self._nodes.values()
            if n.parent_id == parent_id and (branch is None or n.branch == branch)
        )

    def _rain_day_id(self, day: date) -> str:
        return f"rain-day-{day.isoformat()}"

    def ensure_rain_day(self, day: Optional[date] = None) -> TreeNode:
        day = day or date.today()
        day_id = self._rain_day_id(day)
        existing = self._nodes.get(day_id)
        if existing:
            return existing
        title = day.strftime("%A, %B %d, %Y")
        node = TreeNode(
            id=day_id,
            title=title,
            text="",
            branch="rain",
            node_type="rain_day",
            parent_id=None,
            sort_order=int(day.strftime("%Y%m%d")),
        )
        self._nodes[day_id] = node
        self._persist()
        return node

    def quick_capture(self, text: str, *, tags: Optional[list[str]] = None) -> TreeNode:
        text = text.strip()
        if not text:
            raise ValueError("Capture text cannot be empty")
        day_node = self.ensure_rain_day()
        now = datetime.now()
        first_line = text.splitlines()[0][:80]
        title = first_line if first_line else now.strftime("Capture %H:%M")
        node = TreeNode(
            id=_new_id("rain"),
            title=title,
            text=text,
            branch="rain",
            node_type="rain_capture",
            parent_id=day_node.id,
            tags=tags or [],
            created_at=now.replace(tzinfo=timezone.utc).replace(microsecond=0).isoformat(),
        )
        self._nodes[node.id] = node
        day_node.updated_at = _utc_now_iso()
        self._persist()
        return node

    def create_node(
        self,
        *,
        title: str,
        text: str = "",
        branch: str = "rain",
        node_type: str = "note",
        parent_id: Optional[str] = None,
        project_id: Optional[str] = None,
        tags: Optional[list[str]] = None,
    ) -> TreeNode:
        if branch not in BRANCHES:
            raise ValueError(f"Unknown branch: {branch}")
        node = TreeNode(
            id=_new_id(branch[:4]),
            title=title.strip() or "Untitled",
            text=text,
            branch=branch,
            node_type=node_type,
            parent_id=parent_id,
            project_id=project_id,
            tags=tags or [],
        )
        self._nodes[node.id] = node
        self._persist()
        return node

    def update_node(self, node_id: str, **fields: Any) -> TreeNode:
        node = self._nodes.get(node_id)
        if not node:
            raise KeyError(node_id)
        for key, value in fields.items():
            if key == "tags" and isinstance(value, str):
                value = [t.strip() for t in value.split(",") if t.strip()]
            if hasattr(node, key):
                setattr(node, key, value)
        node.updated_at = _utc_now_iso()
        self._persist()
        return node

    def move_node(
        self,
        node_id: str,
        *,
        branch: Optional[str] = None,
        parent_id: Optional[str] = None,
        project_id: Optional[str] = None,
        node_type: Optional[str] = None,
        clear_project: bool = False,
    ) -> TreeNode:
        node = self._nodes.get(node_id)
        if not node:
            raise KeyError(node_id)
        if branch is not None:
            node.branch = branch
        if parent_id is not None or (branch is not None and parent_id is None):
            node.parent_id = parent_id
        if project_id is not None:
            node.project_id = project_id
        if node_type is not None:
            node.node_type = node_type
        if clear_project:
            node.project_id = None
        node.updated_at = _utc_now_iso()
        self._persist()
        return node

    def delete_node(self, node_id: str, *, recursive: bool = False) -> None:
        if node_id not in self._nodes:
            raise KeyError(node_id)
        if recursive:
            child_ids = [n.id for n in self._nodes.values() if n.parent_id == node_id]
            for cid in child_ids:
                self.delete_node(cid, recursive=True)
        del self._nodes[node_id]
        self._persist()

    def set_collapsed(self, node_id: str, collapsed: bool) -> None:
        self.update_node(node_id, collapsed=collapsed)

    def search(
        self,
        query: str = "",
        *,
        branch: Optional[str] = None,
        node_type: Optional[str] = None,
        project_id: Optional[str] = None,
        tags: Optional[list[str]] = None,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[TreeNode]:
        q = query.strip().lower()
        tag_set = {t.lower() for t in (tags or []) if t.strip()}

        def matches(n: TreeNode) -> bool:
            if branch and n.branch != branch:
                return False
            if node_type and n.node_type != node_type:
                return False
            if project_id and n.project_id != project_id:
                return False
            if tag_set and not tag_set.intersection(t.lower() for t in n.tags):
                return False
            created = _parse_iso(n.created_at).date()
            if date_from and created < date_from:
                return False
            if date_to and created > date_to:
                return False
            if q:
                hay = f"{n.title}\n{n.text}\n{' '.join(n.tags)}".lower()
                if q not in hay:
                    return False
            return True

        results = [n for n in self._nodes.values() if matches(n)]
        results.sort(key=lambda n: -_parse_iso(n.updated_at).timestamp())
        return results[offset : offset + limit]

    def all_tags(self) -> list[str]:
        tags: set[str] = set()
        for n in self._nodes.values():
            tags.update(n.tags)
        return sorted(tags, key=str.lower)

    def export_csv(self) -> str:
        buf = io.StringIO()
        writer = csv.DictWriter(buf, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        for node in sorted(self._nodes.values(), key=lambda n: n.created_at):
            row = node.to_dict()
            row["tags"] = ", ".join(node.tags)
            writer.writerow({k: row.get(k, "") for k in CSV_COLUMNS})
        return buf.getvalue()

    def import_csv(self, csv_text: str, *, merge: bool = True) -> tuple[int, int]:
        """Import nodes from CSV. Returns (imported, skipped)."""
        reader = csv.DictReader(io.StringIO(csv_text))
        imported = 0
        skipped = 0
        for row in reader:
            node_id = (row.get("id") or "").strip() or _new_id("import")
            if merge and node_id in self._nodes:
                skipped += 1
                continue
            tags_raw = row.get("tags") or ""
            tags = [t.strip() for t in tags_raw.split(",") if t.strip()]
            node = TreeNode(
                id=node_id,
                title=(row.get("title") or "Imported").strip(),
                text=row.get("text") or "",
                branch=(row.get("branch") or "rain").strip(),
                node_type=(row.get("node_type") or "note").strip(),
                parent_id=(row.get("parent_id") or "").strip() or None,
                project_id=(row.get("project_id") or "").strip() or None,
                tags=tags,
                created_at=(row.get("created_at") or _utc_now_iso()).strip(),
                updated_at=(row.get("updated_at") or _utc_now_iso()).strip(),
                collapsed=str(row.get("collapsed", "")).lower() in ("1", "true", "yes"),
                sort_order=int(row.get("sort_order") or 0),
            )
            self._nodes[node.id] = node
            imported += 1
        if imported:
            self._persist()
        return imported, skipped


def default_store() -> MakerTreeStore:
    import os

    custom = os.environ.get("MAKER_TREE_DATA_DIR", "").strip()
    if custom:
        return MakerTreeStore(Path(custom))
    return MakerTreeStore()
