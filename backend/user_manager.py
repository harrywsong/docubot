"""
User manager for RAG chatbot.

Handles user CRUD operations with SQLite persistence.
"""

import logging
from datetime import datetime
from typing import List, Optional, Tuple
from backend.database import DatabaseManager
from backend.models import User

logger = logging.getLogger(__name__)


class UserManager:
    """Manages users with database persistence."""
    
    def __init__(self, db_manager: DatabaseManager):
        """
        Initialize user manager.
        
        Args:
            db_manager: Database manager instance
        """
        self.db = db_manager
    
    def ensure_default_users(self):
        """
        Ensure default users exist in the database.
        
        Creates Harry, Ryan, and Mom if they don't exist.
        """
        default_users = [
            ("Harry", None),
            ("Ryan", None),
            ("Mom", None)
        ]
        
        for username, profile_picture in default_users:
            try:
                with self.db.transaction() as conn:
                    # Check if user exists
                    cursor = conn.execute(
                        "SELECT id FROM users WHERE username = ?",
                        (username,)
                    )
                    if not cursor.fetchone():
                        # Create user
                        now = datetime.now()
                        conn.execute(
                            """
                            INSERT INTO users (username, profile_picture, created_at, last_active)
                            VALUES (?, ?, ?, ?)
                            """,
                            (username, profile_picture, now, now)
                        )
                        logger.info(f"Created default user: {username}")
            except Exception as e:
                logger.error(f"Failed to create default user {username}: {e}")
    
    def create_user(self, username: str, profile_picture: Optional[str] = None) -> Tuple[bool, str, Optional[User]]:
        """
        Create a new user.
        
        Args:
            username: Username (must be unique)
            profile_picture: Optional profile picture filename
        
        Returns:
            Tuple of (success, message, user)
        """
        # Validate username
        if not username or not isinstance(username, str):
            return False, "Username is required", None
        
        username = username.strip()
        
        if len(username) < 1:
            return False, "Username cannot be empty", None
        
        if len(username) > 50:
            return False, "Username must be 50 characters or less", None
        
        try:
            now = datetime.now()
            
            with self.db.transaction() as conn:
                # Check if username already exists
                cursor = conn.execute(
                    "SELECT id FROM users WHERE username = ?",
                    (username,)
                )
                if cursor.fetchone():
                    return False, f"Username '{username}' already exists", None
                
                # Insert user
                cursor = conn.execute(
                    """
                    INSERT INTO users (username, profile_picture, created_at, last_active)
                    VALUES (?, ?, ?, ?)
                    """,
                    (username, profile_picture, now, now)
                )
                user_id = cursor.lastrowid
            
            logger.info(f"Created user: {username} (ID: {user_id})")
            
            user = User(
                id=user_id,
                username=username,
                profile_picture=profile_picture,
                created_at=now,
                last_active=now
            )
            
            return True, f"User '{username}' created successfully", user
        
        except Exception as e:
            logger.error(f"Failed to create user: {e}")
            return False, f"Failed to create user: {str(e)}", None
    
    def list_users(self) -> List[User]:
        """
        List all users ordered by most recently active.
        
        Returns:
            List of User objects
        """
        with self.db.transaction() as conn:
            cursor = conn.execute(
                """
                SELECT id, username, profile_picture, created_at, last_active
                FROM users
                ORDER BY last_active DESC
                """
            )
            rows = cursor.fetchall()
        
        users = []
        for row in rows:
            users.append(User(
                id=row['id'],
                username=row['username'],
                profile_picture=row['profile_picture'],
                created_at=datetime.fromisoformat(row['created_at']),
                last_active=datetime.fromisoformat(row['last_active'])
            ))
        
        logger.debug(f"Listed {len(users)} users")
        return users
    
    def get_user(self, user_id: int) -> Optional[User]:
        """
        Get a user by ID.
        
        Args:
            user_id: User ID
        
        Returns:
            User object or None if not found
        """
        with self.db.transaction() as conn:
            cursor = conn.execute(
                """
                SELECT id, username, profile_picture, created_at, last_active
                FROM users
                WHERE id = ?
                """,
                (user_id,)
            )
            row = cursor.fetchone()
        
        if not row:
            logger.warning(f"User {user_id} not found")
            return None
        
        return User(
            id=row['id'],
            username=row['username'],
            profile_picture=row['profile_picture'],
            created_at=datetime.fromisoformat(row['created_at']),
            last_active=datetime.fromisoformat(row['last_active'])
        )
    
    def update_user(
        self,
        user_id: int,
        username: Optional[str] = None,
        profile_picture: Optional[str] = None
    ) -> Tuple[bool, str]:
        """
        Update user information.
        
        Args:
            user_id: User ID
            username: New username (optional)
            profile_picture: New profile picture filename (optional)
        
        Returns:
            Tuple of (success, message)
        """
        # Validate inputs
        if username is not None:
            username = username.strip()
            if len(username) < 1:
                return False, "Username cannot be empty"
            if len(username) > 50:
                return False, "Username must be 50 characters or less"
        
        try:
            with self.db.transaction() as conn:
                # Check if user exists
                cursor = conn.execute(
                    "SELECT id FROM users WHERE id = ?",
                    (user_id,)
                )
                if not cursor.fetchone():
                    return False, f"User {user_id} not found"
                
                # Check if new username conflicts with existing user
                if username is not None:
                    cursor = conn.execute(
                        "SELECT id FROM users WHERE username = ? AND id != ?",
                        (username, user_id)
                    )
                    if cursor.fetchone():
                        return False, f"Username '{username}' already exists"
                
                # Build update query
                updates = []
                params = []
                
                if username is not None:
                    updates.append("username = ?")
                    params.append(username)
                
                if profile_picture is not None:
                    updates.append("profile_picture = ?")
                    params.append(profile_picture)
                
                if not updates:
                    return False, "No updates provided"
                
                # Add user_id to params
                params.append(user_id)
                
                # Execute update
                query = f"UPDATE users SET {', '.join(updates)} WHERE id = ?"
                conn.execute(query, params)
            
            logger.info(f"Updated user {user_id}")
            return True, "User updated successfully"
        
        except Exception as e:
            logger.error(f"Failed to update user: {e}")
            return False, f"Failed to update user: {str(e)}"
    
    def update_last_active(self, user_id: int) -> bool:
        """
        Update user's last active timestamp.
        
        Args:
            user_id: User ID
        
        Returns:
            True if updated, False otherwise
        """
        try:
            now = datetime.now()
            
            with self.db.transaction() as conn:
                cursor = conn.execute(
                    "UPDATE users SET last_active = ? WHERE id = ?",
                    (now, user_id)
                )
                updated = cursor.rowcount > 0
            
            if updated:
                logger.debug(f"Updated last_active for user {user_id}")
            
            return updated
        
        except Exception as e:
            logger.error(f"Failed to update last_active: {e}")
            return False
    
    def delete_user(self, user_id: int) -> Tuple[bool, str]:
        """
        Delete a user and all associated data.
        
        This will cascade delete:
        - All conversations
        - All messages
        - All processed files
        
        Args:
            user_id: User ID
        
        Returns:
            Tuple of (success, message)
        """
        try:
            with self.db.transaction() as conn:
                cursor = conn.execute(
                    "DELETE FROM users WHERE id = ?",
                    (user_id,)
                )
                deleted = cursor.rowcount > 0
            
            if deleted:
                logger.info(f"Deleted user {user_id}")
                return True, f"User {user_id} deleted successfully"
            else:
                logger.warning(f"User {user_id} not found for deletion")
                return False, f"User {user_id} not found"
        
        except Exception as e:
            logger.error(f"Failed to delete user: {e}")
            return False, f"Failed to delete user: {str(e)}"
