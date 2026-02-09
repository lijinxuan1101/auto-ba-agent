"""
SQLite 持久化存储：保存对话状态和分析历史
"""

import sqlite3
import json
from datetime import datetime
from typing import Optional, List, Dict, Any
from pathlib import Path


class PersistenceManager:
    """持久化管理器"""
    
    def __init__(self, db_path: str = "ba_agent.db"):
        self.db_path = db_path
        self._init_db()
    
    def _init_db(self):
        """初始化数据库表"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 会话表
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            session_id TEXT PRIMARY KEY,
            created_at TEXT NOT NULL,
            last_active_at TEXT NOT NULL,
            metadata TEXT
        )
        """)
        
        # 对话历史表
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            query TEXT NOT NULL,
            intent TEXT,
            plan TEXT,
            code TEXT,
            result TEXT,
            error TEXT,
            FOREIGN KEY (session_id) REFERENCES sessions(session_id)
        )
        """)
        
        # 数据源表（记录已加载的 Excel 文件）
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS data_sources (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            file_path TEXT NOT NULL,
            loaded_at TEXT NOT NULL,
            profile_summary TEXT,
            semantic_map TEXT,
            FOREIGN KEY (session_id) REFERENCES sessions(session_id)
        )
        """)
        
        conn.commit()
        conn.close()
    
    def create_session(self, session_id: str, metadata: Optional[Dict[str, Any]] = None):
        """创建新会话"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        now = datetime.now().isoformat()
        cursor.execute(
            "INSERT OR REPLACE INTO sessions (session_id, created_at, last_active_at, metadata) VALUES (?, ?, ?, ?)",
            (session_id, now, now, json.dumps(metadata or {}))
        )
        
        conn.commit()
        conn.close()
    
    def update_session_activity(self, session_id: str):
        """更新会话活跃时间"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        now = datetime.now().isoformat()
        cursor.execute(
            "UPDATE sessions SET last_active_at = ? WHERE session_id = ?",
            (now, session_id)
        )
        
        conn.commit()
        conn.close()
    
    def save_conversation(
        self,
        session_id: str,
        query: str,
        intent: str = "",
        plan: str = "",
        code: str = "",
        result: str = "",
        error: str = "",
    ):
        """保存对话记录"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        now = datetime.now().isoformat()
        cursor.execute(
            """INSERT INTO conversations 
            (session_id, timestamp, query, intent, plan, code, result, error)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (session_id, now, query, intent, plan, code, result, error)
        )
        
        conn.commit()
        conn.close()
        
        self.update_session_activity(session_id)
    
    def get_conversation_history(
        self,
        session_id: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """获取对话历史"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute(
            """SELECT * FROM conversations 
            WHERE session_id = ? 
            ORDER BY timestamp DESC 
            LIMIT ?""",
            (session_id, limit)
        )
        
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]
    
    def save_data_source(
        self,
        session_id: str,
        file_path: str,
        profile_summary: str = "",
        semantic_map: str = "",
    ):
        """保存数据源信息"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        now = datetime.now().isoformat()
        cursor.execute(
            """INSERT INTO data_sources 
            (session_id, file_path, loaded_at, profile_summary, semantic_map)
            VALUES (?, ?, ?, ?, ?)""",
            (session_id, file_path, now, profile_summary, semantic_map)
        )
        
        conn.commit()
        conn.close()
    
    def get_data_sources(self, session_id: str) -> List[Dict[str, Any]]:
        """获取会话的数据源列表"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT * FROM data_sources WHERE session_id = ? ORDER BY loaded_at DESC",
            (session_id,)
        )
        
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]
