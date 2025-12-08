"""
SQLite数据库管理模块
用于存储chunk元数据
"""
import sqlite3
import json
import threading
from pathlib import Path
from typing import List, Dict, Optional


class ChunkDatabase:
    """管理chunk元数据的SQLite数据库"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._local = threading.local()
        self._init_db()
    
    def _get_conn(self):
        """获取当前线程的数据库连接"""
        if not hasattr(self._local, 'conn') or self._local.conn is None:
            self._local.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        return self._local.conn
    
    @property
    def conn(self):
        """属性访问器，返回当前线程的连接"""
        return self._get_conn()
    
    def _init_db(self):
        """初始化数据库表结构"""
        conn = self._get_conn()
        cursor = conn.cursor()
        
        # 创建chunks表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS chunks (
                chunk_id TEXT PRIMARY KEY,
                file_id TEXT NOT NULL,
                chunk_index INTEGER NOT NULL,
                text TEXT NOT NULL,
                start_char INTEGER NOT NULL,
                end_char INTEGER NOT NULL,
                token_count INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # 创建索引以提高查询速度
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_file_id ON chunks(file_id)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_chunk_index ON chunks(chunk_index)
        """)
        
        self.conn.commit()
    
    def insert_chunk(self, chunk_data: Dict):
        """插入一个chunk"""
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO chunks 
            (chunk_id, file_id, chunk_index, text, start_char, end_char, token_count)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            chunk_data['chunk_id'],
            chunk_data['file_id'],
            chunk_data['chunk_index'],
            chunk_data['text'],
            chunk_data['start_char'],
            chunk_data['end_char'],
            chunk_data['token_count']
        ))
        self.conn.commit()
    
    def insert_chunks_batch(self, chunks: List[Dict]):
        """批量插入chunks"""
        cursor = self.conn.cursor()
        cursor.executemany("""
            INSERT OR REPLACE INTO chunks 
            (chunk_id, file_id, chunk_index, text, start_char, end_char, token_count)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, [
            (
                chunk['chunk_id'],
                chunk['file_id'],
                chunk['chunk_index'],
                chunk['text'],
                chunk['start_char'],
                chunk['end_char'],
                chunk['token_count']
            )
            for chunk in chunks
        ])
        self.conn.commit()
    
    def get_chunk(self, chunk_id: str) -> Optional[Dict]:
        """根据chunk_id获取chunk"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT chunk_id, file_id, chunk_index, text, start_char, end_char, token_count
            FROM chunks WHERE chunk_id = ?
        """, (chunk_id,))
        row = cursor.fetchone()
        if row:
            return {
                'chunk_id': row[0],
                'file_id': row[1],
                'chunk_index': row[2],
                'text': row[3],
                'start_char': row[4],
                'end_char': row[5],
                'token_count': row[6]
            }
        return None
    
    def get_chunks_by_ids(self, chunk_ids: List[str]) -> List[Dict]:
        """根据chunk_id列表获取chunks"""
        if not chunk_ids:
            return []
        
        placeholders = ','.join(['?'] * len(chunk_ids))
        cursor = self.conn.cursor()
        cursor.execute(f"""
            SELECT chunk_id, file_id, chunk_index, text, start_char, end_char, token_count
            FROM chunks WHERE chunk_id IN ({placeholders})
        """, chunk_ids)
        
        rows = cursor.fetchall()
        return [
            {
                'chunk_id': row[0],
                'file_id': row[1],
                'chunk_index': row[2],
                'text': row[3],
                'start_char': row[4],
                'end_char': row[5],
                'token_count': row[6]
            }
            for row in rows
        ]
    
    def get_file_chunks(self, file_id: str) -> List[Dict]:
        """获取某个文件的所有chunks"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT chunk_id, file_id, chunk_index, text, start_char, end_char, token_count
            FROM chunks WHERE file_id = ? ORDER BY chunk_index
        """, (file_id,))
        
        rows = cursor.fetchall()
        return [
            {
                'chunk_id': row[0],
                'file_id': row[1],
                'chunk_index': row[2],
                'text': row[3],
                'start_char': row[4],
                'end_char': row[5],
                'token_count': row[6]
            }
            for row in rows
        ]
    
    def get_total_chunks(self) -> int:
        """获取chunk总数"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM chunks")
        return cursor.fetchone()[0]
    
    def get_processed_files(self) -> List[str]:
        """获取已处理的文件名列表"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT DISTINCT file_id FROM chunks")
        return [row[0] for row in cursor.fetchall()]
    
    def clear_all(self):
        """清空所有数据"""
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM chunks")
        self.conn.commit()
    
    def close(self):
        """关闭数据库连接"""
        if hasattr(self._local, 'conn') and self._local.conn:
            self._local.conn.close()
            self._local.conn = None



