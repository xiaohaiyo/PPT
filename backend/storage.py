from __future__ import annotations

import json
import math
import re
import uuid
from pathlib import Path
from threading import RLock
from typing import Any

from .config import settings

DOCUMENTS_FILE = settings.data_dir / "documents.json"
TASKS_FILE = settings.data_dir / "tasks.json"
ARTIFACTS_FILE = settings.data_dir / "artifacts.json"
KNOWLEDGE_BASES_FILE = settings.data_dir / "knowledge-bases.json"
SOURCE_SNAPSHOTS_DIR = settings.data_dir / "source-snapshots"
_LOCK = RLock()


def _read(path: Path) -> list[dict[str, Any]]:
    try:
        value = json.loads(path.read_text("utf-8"))
        return value if isinstance(value, list) else []
    except (OSError, json.JSONDecodeError):
        return []


def _write(path: Path, items: list[dict[str, Any]]) -> None:
    temp = path.with_suffix(".tmp")
    temp.write_text(json.dumps(items, ensure_ascii=False, indent=2), "utf-8")
    temp.replace(path)


def list_documents() -> list[dict[str, Any]]:
    return _read(DOCUMENTS_FILE)


def get_document(document_id: str) -> dict[str, Any] | None:
    return next((item for item in list_documents() if item["id"] == document_id), None)


def save_document(item: dict[str, Any]) -> None:
    with _LOCK:
        items = list_documents()
        items.insert(0, item)
        _write(DOCUMENTS_FILE, items)


def delete_document(document_id: str) -> None:
    with _LOCK:
        items = list_documents()
        item = next((x for x in items if x["id"] == document_id), None)
        bases = list_knowledge_bases()
        if item:
            Path(item["path"]).unlink(missing_ok=True)
        _write(DOCUMENTS_FILE, [x for x in items if x["id"] != document_id])
        for base in bases:
            base["document_ids"] = [x for x in base.get("document_ids", []) if x != document_id]
        _write(KNOWLEDGE_BASES_FILE, bases)


def list_knowledge_bases() -> list[dict[str, Any]]:
    return _read(KNOWLEDGE_BASES_FILE)


def save_knowledge_base(item: dict[str, Any]) -> None:
    with _LOCK:
        items = list_knowledge_bases()
        items.insert(0, item)
        _write(KNOWLEDGE_BASES_FILE, items)


def get_knowledge_base(knowledge_base_id: str) -> dict[str, Any] | None:
    return next((item for item in list_knowledge_bases() if item["id"] == knowledge_base_id), None)


def delete_knowledge_base(knowledge_base_id: str) -> None:
    with _LOCK:
        _write(KNOWLEDGE_BASES_FILE, [x for x in list_knowledge_bases() if x["id"] != knowledge_base_id])


def replace_knowledge_base(item: dict[str, Any]) -> None:
    with _LOCK:
        items = list_knowledge_bases()
        items = [item if x["id"] == item["id"] else x for x in items]
        _write(KNOWLEDGE_BASES_FILE, items)


def selected_context(ids: list[str], inline_content: str = "") -> tuple[str, list[dict[str, Any]]]:
    documents = [x for x in list_documents() if x["id"] in ids]
    return context_from_documents(documents, inline_content)


def context_from_documents(documents: list[dict[str, Any]], inline_content: str = "") -> tuple[str, list[dict[str, Any]]]:
    parts = [f'【{x["name"]}】\n{x.get("text", "")}' for x in documents]
    if inline_content.strip():
        parts.append(f"【用户输入】\n{inline_content.strip()}")
    return "\n\n".join(parts), documents


def save_source_snapshot(snapshot_id: str, documents: list[dict[str, Any]], inline_content: str = "") -> None:
    """Persist the exact text scope used by a queued generation."""
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,128}", snapshot_id):
        raise ValueError("invalid source snapshot id")
    SOURCE_SNAPSHOTS_DIR.mkdir(parents=True, exist_ok=True)
    frozen_documents = [
        {key: document.get(key, "") for key in ("id", "name", "text")}
        for document in documents
    ]
    path = SOURCE_SNAPSHOTS_DIR / f"{snapshot_id}.json"
    with _LOCK:
        temp = path.with_suffix(".tmp")
        temp.write_text(json.dumps({"documents": frozen_documents, "inline_content": inline_content}, ensure_ascii=False), "utf-8")
        temp.replace(path)


def load_source_snapshot(snapshot_id: str) -> dict[str, Any] | None:
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,128}", snapshot_id):
        return None
    try:
        value = json.loads((SOURCE_SNAPSHOTS_DIR / f"{snapshot_id}.json").read_text("utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(value, dict) or not isinstance(value.get("documents"), list):
        return None
    return value


def delete_source_snapshot(snapshot_id: str) -> None:
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,128}", snapshot_id):
        return
    (SOURCE_SNAPSHOTS_DIR / f"{snapshot_id}.json").unlink(missing_ok=True)


_LATIN_TOKEN = re.compile(r"[a-z0-9]+(?:[._-][a-z0-9]+)*")
_CJK_RUN = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]+")
_PAGE_MARKER = re.compile(r"^\s*\[?第\s*(\d+)\s*页\]?\s*$")


def _terms(text: str) -> list[str]:
    normalized = text.casefold()
    terms = _LATIN_TOKEN.findall(normalized)
    for run in _CJK_RUN.findall(normalized):
        if len(run) == 1:
            terms.append(run)
        else:
            terms.extend(run[index:index + 2] for index in range(len(run) - 1))
    return terms


def _document_chunks(doc: dict[str, Any]) -> list[dict[str, Any]]:
    chunks = []
    page = None
    buffer = []

    def flush() -> None:
        text = " ".join(part.strip() for part in buffer if part.strip()).strip()
        buffer.clear()
        if len(text) >= 8:
            chunks.append({"document_id": doc["id"], "document_name": doc["name"], "page": page, "quote": text[:700]})

    for raw in doc.get("text", "").splitlines():
        marker = _PAGE_MARKER.match(raw)
        if marker:
            flush()
            page = int(marker.group(1))
        elif not raw.strip():
            flush()
        else:
            buffer.append(raw)
    flush()
    return chunks


def retrieve(
    query: str,
    ids: list[str],
    limit: int = 8,
    inline_content: str = "",
    source_documents: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    if limit <= 0:
        return []
    terms = list(dict.fromkeys(_terms(query)))
    if not terms:
        return []

    selected_ids = set(ids)
    document_pool = list_documents() if source_documents is None else source_documents
    docs = [item for item in document_pool if item["id"] in selected_ids]
    if inline_content.strip():
        docs.append({"id": "inline", "name": "用户输入", "text": inline_content})
    chunks = [chunk for doc in docs for chunk in _document_chunks(doc)]
    if not chunks:
        return []

    tokenized = [_terms(chunk["quote"]) for chunk in chunks]
    document_frequency = {term: sum(term in set(tokens) for tokens in tokenized) for term in terms}
    average_length = sum(map(len, tokenized)) / len(tokenized) or 1
    ranked = []
    for chunk, tokens in zip(chunks, tokenized):
        frequencies = {term: tokens.count(term) for term in terms}
        present = [term for term, frequency in frequencies.items() if frequency]
        if not present:
            continue
        length_norm = 0.25 + 0.75 * len(tokens) / average_length
        score = 0.0
        for term in present:
            idf = math.log(1 + (len(chunks) - document_frequency[term] + 0.5) / (document_frequency[term] + 0.5))
            tf = frequencies[term]
            score += idf * (tf * 2.2) / (tf + 1.2 * length_norm)
        coverage = len(present) / len(terms)
        ranked.append({**chunk, "score": round(score * (0.5 + coverage), 6), "coverage": round(coverage, 4)})
    return sorted(ranked, key=lambda item: (-item["score"], -item["coverage"], item["document_name"], item["quote"]))[:limit]


def list_tasks() -> list[dict[str, Any]]:
    return _read(TASKS_FILE)


def put_task(task: dict[str, Any]) -> None:
    with _LOCK:
        items = list_tasks()
        items = [x for x in items if x["id"] != task["id"]]
        items.insert(0, task)
        _write(TASKS_FILE, items[:100])


def get_task(task_id: str) -> dict[str, Any] | None:
    return next((x for x in list_tasks() if x["id"] == task_id), None)


def delete_task(task_id: str) -> None:
    with _LOCK:
        task = get_task(task_id)
        if task and task.get("artifact_id"):
            delete_artifact(task["artifact_id"])
        remaining = [x for x in list_tasks() if x["id"] != task_id]
        _write(TASKS_FILE, remaining)
        snapshot_id = ((task or {}).get("source_snapshot") or {}).get("snapshot_id")
        if snapshot_id and not any((x.get("source_snapshot") or {}).get("snapshot_id") == snapshot_id for x in remaining):
            delete_source_snapshot(snapshot_id)


def save_artifact(path: Path, kind: str, name: str) -> dict[str, Any]:
    with _LOCK:
        item = {"id": str(uuid.uuid4()), "path": str(path.resolve()), "kind": kind, "name": name, "size": path.stat().st_size}
        items = _read(ARTIFACTS_FILE)
        items.insert(0, item)
        _write(ARTIFACTS_FILE, items)
        return item


def get_artifact(artifact_id: str) -> dict[str, Any] | None:
    return next((x for x in _read(ARTIFACTS_FILE) if x["id"] == artifact_id), None)


def update_artifact(artifact_id: str, **changes) -> dict[str, Any] | None:
    with _LOCK:
        items = _read(ARTIFACTS_FILE)
        item = next((x for x in items if x["id"] == artifact_id), None)
        if not item:
            return None
        item.update(changes)
        _write(ARTIFACTS_FILE, items)
        return item


def delete_artifact(artifact_id: str) -> None:
    with _LOCK:
        items = _read(ARTIFACTS_FILE)
        item = next((x for x in items if x["id"] == artifact_id), None)
        if item:
            Path(item["path"]).unlink(missing_ok=True)
        _write(ARTIFACTS_FILE, [x for x in items if x["id"] != artifact_id])
