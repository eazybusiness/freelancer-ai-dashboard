"""
Bid History Database - SQLite-based storage for bid tracking and learning.

Tracks:
- All generated bids with metadata
- Bid outcomes (pending, viewed, engaged, won, rejected)
- Prompt versions used
- Success metrics for learning
"""

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "data" / "bid_history.db"


def _get_connection() -> sqlite3.Connection:
    """Get a database connection, creating tables if needed."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    _ensure_tables(conn)
    return conn


def _ensure_tables(conn: sqlite3.Connection) -> None:
    """Create tables if they don't exist."""
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS bids (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            
            -- Project info
            project_id INTEGER,
            project_title TEXT NOT NULL,
            project_url TEXT,
            project_description TEXT,
            project_type TEXT,
            project_language TEXT,
            project_budget_min REAL,
            project_budget_max REAL,
            
            -- Bid content
            bid_text TEXT NOT NULL,
            milestone_plan TEXT,
            
            -- Generation metadata
            prompt_version TEXT NOT NULL,
            model_used TEXT,
            tone TEXT,
            
            -- Outcome tracking
            outcome TEXT DEFAULT 'pending',
            outcome_updated_at TEXT,
            outcome_notes TEXT,
            
            -- Success metrics
            was_viewed INTEGER DEFAULT 0,
            was_engaged INTEGER DEFAULT 0,
            was_won INTEGER DEFAULT 0,
            was_high_rank INTEGER DEFAULT 0,
            
            -- Learning data
            user_edits TEXT,
            final_bid_text TEXT,
            feedback_notes TEXT
        );
        
        CREATE TABLE IF NOT EXISTS prompt_versions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            version_key TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            description TEXT,
            created_at TEXT NOT NULL,
            is_active INTEGER DEFAULT 0,
            is_approved INTEGER DEFAULT 0,
            
            -- Stats
            total_bids INTEGER DEFAULT 0,
            won_bids INTEGER DEFAULT 0,
            engaged_bids INTEGER DEFAULT 0,
            viewed_bids INTEGER DEFAULT 0,
            success_rate REAL DEFAULT 0.0
        );
        
        CREATE INDEX IF NOT EXISTS idx_bids_project_id ON bids(project_id);
        CREATE INDEX IF NOT EXISTS idx_bids_outcome ON bids(outcome);
        CREATE INDEX IF NOT EXISTS idx_bids_prompt_version ON bids(prompt_version);
        CREATE INDEX IF NOT EXISTS idx_bids_created_at ON bids(created_at);
    """)
    conn.commit()


# ----- Bid CRUD -----

def save_bid(
    project_title: str,
    bid_text: str,
    prompt_version: str,
    project_id: Optional[int] = None,
    project_url: Optional[str] = None,
    project_description: Optional[str] = None,
    project_type: Optional[str] = None,
    project_language: Optional[str] = None,
    project_budget_min: Optional[float] = None,
    project_budget_max: Optional[float] = None,
    milestone_plan: Optional[Dict] = None,
    model_used: Optional[str] = None,
    tone: Optional[str] = None,
) -> int:
    """Save a new bid to the database. Returns the bid ID."""
    
    conn = _get_connection()
    now = datetime.now(timezone.utc).isoformat()
    
    cursor = conn.execute("""
        INSERT INTO bids (
            created_at, updated_at,
            project_id, project_title, project_url, project_description,
            project_type, project_language, project_budget_min, project_budget_max,
            bid_text, milestone_plan, prompt_version, model_used, tone
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        now, now,
        project_id, project_title, project_url, project_description,
        project_type, project_language, project_budget_min, project_budget_max,
        bid_text,
        json.dumps(milestone_plan) if milestone_plan else None,
        prompt_version, model_used, tone,
    ))
    
    bid_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    # Update prompt version stats
    _increment_prompt_stat(prompt_version, "total_bids")
    
    return bid_id


def get_bid(bid_id: int) -> Optional[Dict[str, Any]]:
    """Get a single bid by ID."""
    conn = _get_connection()
    row = conn.execute("SELECT * FROM bids WHERE id = ?", (bid_id,)).fetchone()
    conn.close()
    
    if row is None:
        return None
    
    return _row_to_dict(row)


def get_recent_bids(limit: int = 50) -> List[Dict[str, Any]]:
    """Get recent bids, newest first."""
    conn = _get_connection()
    rows = conn.execute(
        "SELECT * FROM bids ORDER BY created_at DESC LIMIT ?",
        (limit,)
    ).fetchall()
    conn.close()
    
    return [_row_to_dict(row) for row in rows]


def get_bids_by_outcome(outcome: str, limit: int = 50) -> List[Dict[str, Any]]:
    """Get bids filtered by outcome."""
    conn = _get_connection()
    rows = conn.execute(
        "SELECT * FROM bids WHERE outcome = ? ORDER BY created_at DESC LIMIT ?",
        (outcome, limit)
    ).fetchall()
    conn.close()
    
    return [_row_to_dict(row) for row in rows]


def get_winning_bids(limit: int = 50) -> List[Dict[str, Any]]:
    """Get bids marked as won - these are the gold standard for learning."""
    conn = _get_connection()
    rows = conn.execute(
        "SELECT * FROM bids WHERE was_won = 1 ORDER BY created_at DESC LIMIT ?",
        (limit,)
    ).fetchall()
    conn.close()
    
    return [_row_to_dict(row) for row in rows]


def get_successful_bids(limit: int = 50) -> List[Dict[str, Any]]:
    """Get bids that had positive outcomes (engaged or won)."""
    conn = _get_connection()
    rows = conn.execute(
        """SELECT * FROM bids 
           WHERE was_engaged = 1 OR was_won = 1 
           ORDER BY was_won DESC, was_engaged DESC, created_at DESC 
           LIMIT ?""",
        (limit,)
    ).fetchall()
    conn.close()
    
    return [_row_to_dict(row) for row in rows]


def search_bids_by_type(project_type: str, limit: int = 20) -> List[Dict[str, Any]]:
    """Find similar past bids by project type."""
    conn = _get_connection()
    rows = conn.execute(
        """SELECT * FROM bids 
           WHERE project_type = ? 
           ORDER BY was_won DESC, was_engaged DESC, was_viewed DESC, created_at DESC 
           LIMIT ?""",
        (project_type, limit)
    ).fetchall()
    conn.close()
    
    return [_row_to_dict(row) for row in rows]


# ----- Outcome Tracking -----

def update_bid_outcome(
    bid_id: int,
    outcome: str,
    was_viewed: bool = False,
    was_engaged: bool = False,
    was_won: bool = False,
    was_high_rank: bool = False,
    notes: Optional[str] = None,
) -> bool:
    """Update the outcome of a bid. Returns True if successful."""
    
    conn = _get_connection()
    now = datetime.now(timezone.utc).isoformat()
    
    # Get current bid to find prompt version
    row = conn.execute("SELECT prompt_version, was_viewed, was_engaged, was_won FROM bids WHERE id = ?", (bid_id,)).fetchone()
    if row is None:
        conn.close()
        return False
    
    prompt_version = row["prompt_version"]
    prev_viewed = row["was_viewed"]
    prev_engaged = row["was_engaged"]
    prev_won = row["was_won"]
    
    conn.execute("""
        UPDATE bids SET
            outcome = ?,
            outcome_updated_at = ?,
            outcome_notes = ?,
            was_viewed = ?,
            was_engaged = ?,
            was_won = ?,
            was_high_rank = ?,
            updated_at = ?
        WHERE id = ?
    """, (
        outcome, now, notes,
        1 if was_viewed else 0,
        1 if was_engaged else 0,
        1 if was_won else 0,
        1 if was_high_rank else 0,
        now, bid_id
    ))
    
    conn.commit()
    conn.close()
    
    # Update prompt version stats (only increment, not decrement)
    if was_viewed and not prev_viewed:
        _increment_prompt_stat(prompt_version, "viewed_bids")
    if was_engaged and not prev_engaged:
        _increment_prompt_stat(prompt_version, "engaged_bids")
    if was_won and not prev_won:
        _increment_prompt_stat(prompt_version, "won_bids")
    
    _recalculate_prompt_success_rate(prompt_version)
    
    return True


def save_final_bid(bid_id: int, final_text: str, feedback: Optional[str] = None) -> bool:
    """Save the final edited version of a bid for learning."""
    conn = _get_connection()
    now = datetime.now(timezone.utc).isoformat()
    
    # Get original bid text
    row = conn.execute("SELECT bid_text FROM bids WHERE id = ?", (bid_id,)).fetchone()
    if row is None:
        conn.close()
        return False
    
    original = row["bid_text"]
    edits = None
    if original != final_text:
        edits = json.dumps({"original": original, "final": final_text})
    
    conn.execute("""
        UPDATE bids SET
            final_bid_text = ?,
            user_edits = ?,
            feedback_notes = ?,
            updated_at = ?
        WHERE id = ?
    """, (final_text, edits, feedback, now, bid_id))
    
    conn.commit()
    conn.close()
    return True


# ----- Prompt Version Management -----

def register_prompt_version(
    version_key: str,
    name: str,
    description: Optional[str] = None,
    is_active: bool = False,
    is_approved: bool = False,
) -> bool:
    """Register a new prompt version in the database."""
    conn = _get_connection()
    now = datetime.now(timezone.utc).isoformat()
    
    try:
        conn.execute("""
            INSERT INTO prompt_versions (version_key, name, description, created_at, is_active, is_approved)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (version_key, name, description, now, 1 if is_active else 0, 1 if is_approved else 0))
        conn.commit()
    except sqlite3.IntegrityError:
        # Already exists, update it
        conn.execute("""
            UPDATE prompt_versions SET name = ?, description = ?, is_active = ?, is_approved = ?
            WHERE version_key = ?
        """, (name, description, 1 if is_active else 0, 1 if is_approved else 0, version_key))
        conn.commit()
    
    conn.close()
    return True


def get_prompt_versions() -> List[Dict[str, Any]]:
    """Get all registered prompt versions with their stats."""
    conn = _get_connection()
    rows = conn.execute(
        "SELECT * FROM prompt_versions ORDER BY is_active DESC, is_approved DESC, success_rate DESC"
    ).fetchall()
    conn.close()
    
    return [dict(row) for row in rows]


def get_active_prompt_version() -> Optional[str]:
    """Get the currently active prompt version key."""
    conn = _get_connection()
    row = conn.execute(
        "SELECT version_key FROM prompt_versions WHERE is_active = 1 LIMIT 1"
    ).fetchone()
    conn.close()
    
    return row["version_key"] if row else None


def set_active_prompt_version(version_key: str) -> bool:
    """Set a prompt version as active (deactivates others)."""
    conn = _get_connection()
    conn.execute("UPDATE prompt_versions SET is_active = 0")
    conn.execute("UPDATE prompt_versions SET is_active = 1 WHERE version_key = ?", (version_key,))
    conn.commit()
    conn.close()
    return True


def approve_prompt_version(version_key: str) -> bool:
    """Mark a prompt version as approved (tested and working well)."""
    conn = _get_connection()
    conn.execute("UPDATE prompt_versions SET is_approved = 1 WHERE version_key = ?", (version_key,))
    conn.commit()
    conn.close()
    return True


def _increment_prompt_stat(version_key: str, stat_name: str) -> None:
    """Increment a stat for a prompt version."""
    conn = _get_connection()
    conn.execute(
        f"UPDATE prompt_versions SET {stat_name} = {stat_name} + 1 WHERE version_key = ?",
        (version_key,)
    )
    conn.commit()
    conn.close()


def _recalculate_prompt_success_rate(version_key: str) -> None:
    """Recalculate the success rate for a prompt version."""
    conn = _get_connection()
    row = conn.execute(
        "SELECT total_bids, won_bids, engaged_bids, viewed_bids FROM prompt_versions WHERE version_key = ?",
        (version_key,)
    ).fetchone()
    
    if row and row["total_bids"] > 0:
        # Weighted score: won=3, engaged=2, viewed=1
        weighted = (row["won_bids"] * 3 + row["engaged_bids"] * 2 + row["viewed_bids"]) / (row["total_bids"] * 3)
        success_rate = min(1.0, weighted)
        
        conn.execute(
            "UPDATE prompt_versions SET success_rate = ? WHERE version_key = ?",
            (success_rate, version_key)
        )
        conn.commit()
    
    conn.close()


# ----- Analytics -----

def get_learning_stats() -> Dict[str, Any]:
    """Get overall learning statistics."""
    conn = _get_connection()
    
    total = conn.execute("SELECT COUNT(*) as c FROM bids").fetchone()["c"]
    won = conn.execute("SELECT COUNT(*) as c FROM bids WHERE was_won = 1").fetchone()["c"]
    engaged = conn.execute("SELECT COUNT(*) as c FROM bids WHERE was_engaged = 1").fetchone()["c"]
    viewed = conn.execute("SELECT COUNT(*) as c FROM bids WHERE was_viewed = 1").fetchone()["c"]
    pending = conn.execute("SELECT COUNT(*) as c FROM bids WHERE outcome = 'pending'").fetchone()["c"]
    
    # By project type
    by_type = conn.execute("""
        SELECT project_type, COUNT(*) as total,
               SUM(was_won) as won, SUM(was_engaged) as engaged, SUM(was_viewed) as viewed
        FROM bids
        WHERE project_type IS NOT NULL
        GROUP BY project_type
    """).fetchall()
    
    conn.close()
    
    return {
        "total_bids": total,
        "won": won,
        "engaged": engaged,
        "viewed": viewed,
        "pending": pending,
        "win_rate": (won / total * 100) if total > 0 else 0,
        "engagement_rate": (engaged / total * 100) if total > 0 else 0,
        "by_type": [dict(row) for row in by_type],
    }


# ----- Helpers -----

def _row_to_dict(row: sqlite3.Row) -> Dict[str, Any]:
    """Convert a database row to a dictionary with parsed JSON fields."""
    d = dict(row)
    
    # Parse JSON fields
    if d.get("milestone_plan"):
        try:
            d["milestone_plan"] = json.loads(d["milestone_plan"])
        except json.JSONDecodeError:
            pass
    
    if d.get("user_edits"):
        try:
            d["user_edits"] = json.loads(d["user_edits"])
        except json.JSONDecodeError:
            pass
    
    return d
