"""SQLite-based memory store for conversation history and system state.

Stores conversations, user preferences, and system state for persistent memory.
"""

import logging
import sqlite3
import json
from datetime import datetime
from typing import List, Dict, Optional
import os

logger = logging.getLogger(__name__)


class MemoryStore:
    """SQLite-based storage for henzai's memory and state."""
    
    def __init__(self, db_path: Optional[str] = None):
        """
        Initialize the memory store.
        
        Args:
            db_path: Path to SQLite database file
                    (default: ~/.local/share/henzai/memory.db)
        """
        if db_path is None:
            data_dir = os.path.expanduser("~/.local/share/henzai")
            os.makedirs(data_dir, exist_ok=True)
            db_path = os.path.join(data_dir, "memory.db")
        
        self.db_path = db_path
        self.current_session_id = None  # Track active session
        logger.info(f"Initializing memory store at: {db_path}")
        
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._init_database()
        
        # Create or load current session
        self._start_new_session()
    
    def _init_database(self):
        """Initialize database schema."""
        cursor = self.conn.cursor()
        
        # Sessions table - groups related conversations
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                message_count INTEGER DEFAULT 0
            )
        ''')
        
        # Conversations table - now linked to sessions
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                user_message TEXT NOT NULL,
                assistant_response TEXT NOT NULL,
                context_json TEXT,
                FOREIGN KEY (session_id) REFERENCES sessions (id) ON DELETE CASCADE
            )
        ''')
        
        # Create index for faster session queries
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_conversations_session 
            ON conversations(session_id)
        ''')
        
        # Settings table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Action history table (for future learning)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS action_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                action_type TEXT NOT NULL,
                parameters TEXT,
                outcome TEXT,
                success BOOLEAN
            )
        ''')
        
        self.conn.commit()
        logger.info("Database schema initialized")
    
    def add_conversation(self, user_message: str, assistant_response: str, context: Optional[Dict] = None):
        """
        Store a conversation turn in the current session.
        
        Args:
            user_message: User's message
            assistant_response: Assistant's response
            context: Optional context dictionary
        """
        try:
            cursor = self.conn.cursor()
            context_json = json.dumps(context) if context else None
            
            cursor.execute('''
                INSERT INTO conversations (session_id, user_message, assistant_response, context_json)
                VALUES (?, ?, ?, ?)
            ''', (self.current_session_id, user_message, assistant_response, context_json))
            
            self.conn.commit()
            logger.debug(f"Stored conversation in session {self.current_session_id} (ID: {cursor.lastrowid})")
            
        except Exception as e:
            logger.error(f"Error storing conversation: {e}", exc_info=True)
            self.conn.rollback()
    
    def get_recent_context(self, limit: int = 10) -> List[Dict[str, str]]:
        """
        Get recent conversation history from current session.
        
        Args:
            limit: Number of recent conversations to retrieve
            
        Returns:
            List of conversation dictionaries with 'user' and 'assistant' keys
        """
        try:
            cursor = self.conn.cursor()
            cursor.execute('''
                SELECT user_message, assistant_response
                FROM conversations
                WHERE session_id = ?
                ORDER BY timestamp DESC
                LIMIT ?
            ''', (self.current_session_id, limit))
            
            rows = cursor.fetchall()
            
            # Reverse to get chronological order
            context = []
            for row in reversed(rows):
                context.append({
                    'user': row['user_message'],
                    'assistant': row['assistant_response']
                })
            
            logger.debug(f"Retrieved {len(context)} conversation turns from session {self.current_session_id}")
            return context
            
        except Exception as e:
            logger.error(f"Error retrieving context: {e}", exc_info=True)
            return []
    
    def get_history(self, limit: Optional[int] = None) -> List[Dict[str, str]]:
        """
        Get conversation history in messages format (for APIs/UI).
        
        Args:
            limit: Number of recent conversations to retrieve (None for all)
            
        Returns:
            List of message dictionaries with 'role' and 'content' keys,
            in chronological order (oldest first).
        """
        try:
            cursor = self.conn.cursor()
            
            if limit:
                cursor.execute('''
                    SELECT user_message, assistant_response
                    FROM conversations
                    WHERE session_id = ?
                    ORDER BY timestamp DESC
                    LIMIT ?
                ''', (self.current_session_id, limit))
            else:
                cursor.execute('''
                    SELECT user_message, assistant_response
                    FROM conversations
                    WHERE session_id = ?
                    ORDER BY timestamp ASC
                ''', (self.current_session_id,))
            
            rows = cursor.fetchall()
            
            # Convert to messages format
            messages = []
            for row in (reversed(rows) if limit else rows):
                messages.append({
                    'role': 'user',
                    'content': row['user_message']
                })
                messages.append({
                    'role': 'assistant',
                    'content': row['assistant_response']
                })
            
            logger.debug(f"Retrieved {len(messages)} messages from session {self.current_session_id}")
            return messages
        except Exception as e:
            logger.error(f"Error retrieving history: {e}", exc_info=True)
            return []
    
    def get_all_conversations(self, limit: Optional[int] = None) -> List[Dict]:
        """
        Get all conversations.
        
        Args:
            limit: Optional limit on number of conversations
            
        Returns:
            List of conversation dictionaries
        """
        try:
            cursor = self.conn.cursor()
            
            if limit:
                cursor.execute('''
                    SELECT id, timestamp, user_message, assistant_response
                    FROM conversations
                    ORDER BY timestamp DESC
                    LIMIT ?
                ''', (limit,))
            else:
                cursor.execute('''
                    SELECT id, timestamp, user_message, assistant_response
                    FROM conversations
                    ORDER BY timestamp DESC
                ''')
            
            rows = cursor.fetchall()
            
            conversations = []
            for row in rows:
                conversations.append({
                    'id': row['id'],
                    'timestamp': row['timestamp'],
                    'user_message': row['user_message'],
                    'assistant_response': row['assistant_response']
                })
            
            return conversations
            
        except Exception as e:
            logger.error(f"Error retrieving conversations: {e}", exc_info=True)
            return []
    
    def _start_new_session(self):
        """Create a new session and set it as current."""
        try:
            cursor = self.conn.cursor()
            cursor.execute('''
                INSERT INTO sessions (title, message_count)
                VALUES (?, ?)
            ''', ("New Chat", 0))
            self.conn.commit()
            self.current_session_id = cursor.lastrowid
            logger.info(f"Started new session (ID: {self.current_session_id})")
        except Exception as e:
            logger.error(f"Error starting session: {e}", exc_info=True)
    
    def save_current_session(self, title: Optional[str] = None):
        """
        Save current session with optional title.
        
        Args:
            title: Optional title for the session (auto-generated if None)
        """
        if not self.current_session_id:
            return
        
        try:
            cursor = self.conn.cursor()
            
            # Get first user message for auto-title if not provided
            if not title:
                cursor.execute('''
                    SELECT user_message FROM conversations
                    WHERE session_id = ?
                    ORDER BY timestamp ASC LIMIT 1
                ''', (self.current_session_id,))
                row = cursor.fetchone()
                if row:
                    # Use first 50 chars of first message
                    title = row['user_message'][:50]
                    if len(row['user_message']) > 50:
                        title += "..."
                else:
                    title = "Empty Chat"
            
            # Update session title and message count
            cursor.execute('''
                UPDATE sessions 
                SET title = ?,
                    updated_at = CURRENT_TIMESTAMP,
                    message_count = (
                        SELECT COUNT(*) FROM conversations 
                        WHERE session_id = ?
                    )
                WHERE id = ?
            ''', (title, self.current_session_id, self.current_session_id))
            
            self.conn.commit()
            logger.info(f"Saved session {self.current_session_id}: {title}")
            
        except Exception as e:
            logger.error(f"Error saving session: {e}", exc_info=True)
    
    def list_sessions(self, limit: int = 50) -> List[Dict]:
        """
        List all saved sessions.
        
        Args:
            limit: Maximum number of sessions to return
            
        Returns:
            List of session dictionaries with id, title, timestamps, message_count
        """
        try:
            cursor = self.conn.cursor()
            cursor.execute('''
                SELECT id, title, created_at, updated_at, message_count
                FROM sessions
                WHERE message_count > 0
                ORDER BY updated_at DESC
                LIMIT ?
            ''', (limit,))
            
            rows = cursor.fetchall()
            sessions = []
            for row in rows:
                sessions.append({
                    'id': row['id'],
                    'title': row['title'] or "Untitled Chat",
                    'created_at': row['created_at'],
                    'updated_at': row['updated_at'],
                    'message_count': row['message_count']
                })
            
            return sessions
            
        except Exception as e:
            logger.error(f"Error listing sessions: {e}", exc_info=True)
            return []
    
    def load_session(self, session_id: int) -> List[Dict[str, str]]:
        """
        Load conversation history from a specific session.
        
        Args:
            session_id: ID of session to load
            
        Returns:
            List of conversation dictionaries with 'user' and 'assistant' keys
        """
        try:
            cursor = self.conn.cursor()
            cursor.execute('''
                SELECT user_message, assistant_response
                FROM conversations
                WHERE session_id = ?
                ORDER BY timestamp ASC
            ''', (session_id,))
            
            rows = cursor.fetchall()
            context = []
            for row in rows:
                context.append({
                    'user': row['user_message'],
                    'assistant': row['assistant_response']
                })
            
            # Set as current session
            self.current_session_id = session_id
            logger.info(f"Loaded session {session_id} with {len(context)} messages")
            return context
            
        except Exception as e:
            logger.error(f"Error loading session: {e}", exc_info=True)
            return []
    
    def delete_session(self, session_id: int):
        """
        Delete a session and all its conversations.
        
        Args:
            session_id: ID of session to delete
        """
        try:
            cursor = self.conn.cursor()
            cursor.execute('DELETE FROM sessions WHERE id = ?', (session_id,))
            # Conversations cascade delete automatically
            self.conn.commit()
            logger.info(f"Deleted session {session_id}")
            
            # If deleted current session, start new one
            if session_id == self.current_session_id:
                self._start_new_session()
                
        except Exception as e:
            logger.error(f"Error deleting session: {e}", exc_info=True)
            self.conn.rollback()
    
    def clear_history(self):
        """Clear all conversation history and start fresh session."""
        try:
            # Save current session before clearing
            if self.current_session_id:
                self.save_current_session()
            
            # Start new session
            self._start_new_session()
            logger.info("Started new session (history preserved)")
        except Exception as e:
            logger.error(f"Error clearing history: {e}", exc_info=True)
    
    def get_setting(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """
        Get a setting value.
        
        Args:
            key: Setting key
            default: Default value if not found
            
        Returns:
            Setting value or default
        """
        try:
            cursor = self.conn.cursor()
            cursor.execute('SELECT value FROM settings WHERE key = ?', (key,))
            row = cursor.fetchone()
            
            if row:
                return row['value']
            return default
            
        except Exception as e:
            logger.error(f"Error getting setting {key}: {e}", exc_info=True)
            return default
    
    def set_setting(self, key: str, value: str):
        """
        Set a setting value.
        
        Args:
            key: Setting key
            value: Setting value
        """
        try:
            cursor = self.conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO settings (key, value, updated_at)
                VALUES (?, ?, CURRENT_TIMESTAMP)
            ''', (key, value))
            
            self.conn.commit()
            logger.debug(f"Set setting: {key} = {value}")
            
        except Exception as e:
            logger.error(f"Error setting {key}: {e}", exc_info=True)
            self.conn.rollback()
    
    def log_action(self, action_type: str, parameters: Dict, outcome: str, success: bool):
        """
        Log an action for future learning and analysis.
        
        Args:
            action_type: Type of action (e.g., "launch_app", "adjust_setting")
            parameters: Action parameters
            outcome: Result/outcome of the action
            success: Whether the action succeeded
        """
        try:
            cursor = self.conn.cursor()
            parameters_json = json.dumps(parameters)
            
            cursor.execute('''
                INSERT INTO action_history (action_type, parameters, outcome, success)
                VALUES (?, ?, ?, ?)
            ''', (action_type, parameters_json, outcome, success))
            
            self.conn.commit()
            logger.debug(f"Logged action: {action_type}")
            
        except Exception as e:
            logger.error(f"Error logging action: {e}", exc_info=True)
            self.conn.rollback()
    
    def get_action_history(self, limit: int = 100) -> List[Dict]:
        """
        Get recent action history.
        
        Args:
            limit: Number of actions to retrieve
            
        Returns:
            List of action dictionaries
        """
        try:
            cursor = self.conn.cursor()
            cursor.execute('''
                SELECT id, timestamp, action_type, parameters, outcome, success
                FROM action_history
                ORDER BY timestamp DESC
                LIMIT ?
            ''', (limit,))
            
            rows = cursor.fetchall()
            
            actions = []
            for row in rows:
                actions.append({
                    'id': row['id'],
                    'timestamp': row['timestamp'],
                    'action_type': row['action_type'],
                    'parameters': json.loads(row['parameters']) if row['parameters'] else {},
                    'outcome': row['outcome'],
                    'success': bool(row['success'])
                })
            
            return actions
            
        except Exception as e:
            logger.error(f"Error retrieving action history: {e}", exc_info=True)
            return []
    
    def close(self):
        """Close the database connection."""
        if self.conn:
            self.conn.close()
            logger.info("Database connection closed")
    
    def __del__(self):
        """Cleanup on deletion."""
        self.close()










