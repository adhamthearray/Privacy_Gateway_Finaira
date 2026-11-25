from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from sqlalchemy import Boolean, Column, Integer, MetaData, String, Table, Text, create_engine, event, func, select

from common import DATA


def _database_url() -> tuple[str, str]:
    configured = os.environ.get("DATABASE_URL", "").strip()
    if configured:
        if configured.startswith("postgres://"):
            configured = "postgresql+psycopg://" + configured[len("postgres://") :]
        elif configured.startswith("postgresql://"):
            configured = "postgresql+psycopg://" + configured[len("postgresql://") :]
        separator = "&" if "?" in configured else "?"
        if "sslmode=" not in configured:
            configured += separator + "sslmode=require"
        return configured, "PostgreSQL via DATABASE_URL"
    path = Path(os.environ.get("ANNOTATION_DB_PATH", str(DATA / "annotations.sqlite3"))).expanduser().resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    return f"sqlite:///{path.as_posix()}", str(path)


DATABASE_URL, DATABASE_DESCRIPTION = _database_url()
_is_sqlite = DATABASE_URL.startswith("sqlite:")
engine_kwargs: dict[str, Any] = {"pool_pre_ping": True}
if _is_sqlite:
    engine_kwargs["connect_args"] = {"check_same_thread": False, "timeout": 30}
else:
    engine_kwargs.update({"pool_size": 3, "max_overflow": 2, "connect_args": {"prepare_threshold": None}})

ENGINE = create_engine(DATABASE_URL, **engine_kwargs)

if _is_sqlite:
    @event.listens_for(ENGINE, "connect")
    def _sqlite_pragmas(dbapi_connection, _connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA busy_timeout=30000")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.close()


metadata = MetaData()
annotations = Table(
    "annotations", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("prompt_id", String(80), nullable=False, index=True),
    Column("reviewer_id", String(120), nullable=False, index=True),
    Column("entity_type", String(40), nullable=False, index=True),
    Column("label", String(30)),
    Column("reason", Text),
    Column("ambiguity", Boolean, nullable=False, default=False),
    Column("notes", Text),
    Column("created_at", String(40), nullable=False, index=True),
)
prompt_actions = Table(
    "prompt_actions", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("prompt_id", String(80), nullable=False, index=True),
    Column("reviewer_id", String(120), nullable=False, index=True),
    Column("action", String(40), nullable=False),
    Column("edited_prompt", Text),
    Column("notes", Text),
    Column("created_at", String(40), nullable=False, index=True),
)
adjudications = Table(
    "adjudications", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("prompt_id", String(80), nullable=False, index=True),
    Column("entity_type", String(40), nullable=False, index=True),
    Column("adjudicator_id", String(120), nullable=False),
    Column("label", String(30), nullable=False),
    Column("reason", Text),
    Column("created_at", String(40), nullable=False, index=True),
)


def initialize() -> None:
    metadata.create_all(ENGINE)


def _dicts(statement) -> list[dict[str, Any]]:
    with ENGINE.connect() as connection:
        return [dict(row._mapping) for row in connection.execute(statement)]


def append_review(prompt_id: str, reviewer_id: str, action: str, edited_prompt: str, notes: str, created_at: str, rows: list[dict]) -> None:
    with ENGINE.begin() as connection:
        connection.execute(prompt_actions.insert().values(
            prompt_id=prompt_id, reviewer_id=reviewer_id, action=action,
            edited_prompt=edited_prompt, notes=notes, created_at=created_at,
        ))
        if rows:
            connection.execute(annotations.insert(), [
                {
                    "prompt_id": prompt_id,
                    "reviewer_id": reviewer_id,
                    "entity_type": row["entity_type"],
                    "label": row["reviewer_label"],
                    "reason": row.get("approved_reason") or "",
                    "ambiguity": bool(row.get("ambiguous")),
                    "notes": notes,
                    "created_at": created_at,
                }
                for row in rows
            ])


def latest_review(prompt_id: str, reviewer_id: str) -> list[dict[str, Any]]:
    latest_time = select(func.max(annotations.c.created_at)).where(
        annotations.c.prompt_id == prompt_id,
        annotations.c.reviewer_id == reviewer_id,
    ).scalar_subquery()
    statement = select(
        annotations.c.entity_type, annotations.c.label, annotations.c.reason, annotations.c.ambiguity
    ).where(
        annotations.c.prompt_id == prompt_id,
        annotations.c.reviewer_id == reviewer_id,
        annotations.c.created_at == latest_time,
    )
    return _dicts(statement)


def latest_annotation_rows() -> list[dict[str, Any]]:
    ranked = select(
        annotations,
        func.row_number().over(
            partition_by=[annotations.c.prompt_id, annotations.c.entity_type, annotations.c.reviewer_id],
            order_by=annotations.c.id.desc(),
        ).label("rn"),
    ).subquery()
    return _dicts(select(
        ranked.c.prompt_id, ranked.c.entity_type, ranked.c.reviewer_id,
        ranked.c.label, ranked.c.reason, ranked.c.ambiguity,
    ).where(ranked.c.rn == 1))


def append_adjudication(prompt_id: str, entity_type: str, adjudicator_id: str, label: str, reason: str, created_at: str) -> None:
    with ENGINE.begin() as connection:
        connection.execute(adjudications.insert().values(
            prompt_id=prompt_id, entity_type=entity_type, adjudicator_id=adjudicator_id,
            label=label, reason=reason, created_at=created_at,
        ))


def latest_adjudication_rows() -> list[dict[str, Any]]:
    ranked = select(
        adjudications,
        func.row_number().over(
            partition_by=[adjudications.c.prompt_id, adjudications.c.entity_type],
            order_by=adjudications.c.id.desc(),
        ).label("rn"),
    ).subquery()
    return _dicts(select(
        ranked.c.prompt_id, ranked.c.entity_type, ranked.c.adjudicator_id,
        ranked.c.label, ranked.c.reason,
    ).where(ranked.c.rn == 1))


def all_annotation_rows() -> list[dict[str, Any]]:
    return _dicts(select(annotations).order_by(annotations.c.id))

