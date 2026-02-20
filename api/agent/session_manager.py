"""
Session Manager for conversation history.

Uses in-memory cache with TTL. Can be extended to use Redis for persistence.
"""

from datetime import datetime, timedelta
from typing import Dict, Optional

from cachetools import TTLCache

from api.agent.models import ConversationSession, SessionMessage


class SessionManager:
    """Manages conversation sessions with TTL-based expiration."""

    def __init__(
        self,
        max_sessions: int = 1000,
        session_ttl_minutes: int = 60,
    ):
        """
        Initialize the session manager.

        Args:
            max_sessions: Maximum number of sessions to keep in cache
            session_ttl_minutes: TTL for sessions in minutes
        """
        self._cache: TTLCache = TTLCache(
            maxsize=max_sessions,
            ttl=session_ttl_minutes * 60,
        )

    def get_or_create_session(
        self,
        session_id: Optional[str] = None,
        user_id: Optional[int] = None,
    ) -> ConversationSession:
        """
        Get an existing session or create a new one.

        Args:
            session_id: Optional session ID to retrieve
            user_id: Optional user ID to associate with the session

        Returns:
            ConversationSession: The session object
        """
        if session_id and session_id in self._cache:
            session = self._cache[session_id]
            session.last_activity = datetime.utcnow()
            return session

        # Create new session
        session = ConversationSession(user_id=user_id)
        self._cache[session.session_id] = session
        return session

    def get_session(self, session_id: str) -> Optional[ConversationSession]:
        """
        Get a session by ID.

        Args:
            session_id: The session ID to retrieve

        Returns:
            ConversationSession or None if not found
        """
        return self._cache.get(session_id)

    def add_message(
        self,
        session_id: str,
        role: str,
        content: str,
    ) -> bool:
        """
        Add a message to a session.

        Args:
            session_id: The session ID
            role: Message role (user or assistant)
            content: Message content

        Returns:
            bool: True if message was added, False if session not found
        """
        session = self._cache.get(session_id)
        if not session:
            return False

        message = SessionMessage(role=role, content=content)
        session.messages.append(message)
        session.last_activity = datetime.utcnow()

        # Keep only last 20 messages to limit context size
        if len(session.messages) > 20:
            session.messages = session.messages[-20:]

        return True

    def get_conversation_context(
        self,
        session_id: str,
        max_messages: int = 10,
    ) -> str:
        """
        Get conversation context as a formatted string.

        Args:
            session_id: The session ID
            max_messages: Maximum number of recent messages to include

        Returns:
            str: Formatted conversation history
        """
        session = self._cache.get(session_id)
        if not session or not session.messages:
            return ""

        recent_messages = session.messages[-max_messages:]
        context_parts = []

        for msg in recent_messages:
            role = "Usuário" if msg.role == "user" else "Assistente"
            context_parts.append(f"{role}: {msg.content}")

        return "\n".join(context_parts)

    def delete_session(self, session_id: str) -> bool:
        """
        Delete a session.

        Args:
            session_id: The session ID to delete

        Returns:
            bool: True if deleted, False if not found
        """
        if session_id in self._cache:
            del self._cache[session_id]
            return True
        return False

    def clear_all_sessions(self) -> int:
        """
        Clear all sessions.

        Returns:
            int: Number of sessions cleared
        """
        count = len(self._cache)
        self._cache.clear()
        return count

    @property
    def active_sessions_count(self) -> int:
        """Get the number of active sessions."""
        return len(self._cache)


# Global session manager instance
session_manager = SessionManager()
