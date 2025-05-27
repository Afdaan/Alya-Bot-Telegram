"""Update Git and manage Alya Bot deployment via Telegram commands."""

import asyncio
import logging
import os
import html
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from telegram import Update
from telegram.ext import CallbackContext, CommandHandler
from telegram.constants import ParseMode

logger = logging.getLogger(__name__)


class DeploymentManager:
    """Enterprise-grade admin handler for Alya Bot deployment management."""
    
    def __init__(self, tmux_session: Optional[str] = None):
        """Initialize admin handler with auto-detected project path.
        
        Args:
            tmux_session: Name of the tmux session running the bot
        """
        self.project_path = self._detect_project_path()
        self.tmux_session = tmux_session or self._detect_tmux_session()
        self.max_commit_display = 10
        self.authorized_users = self._load_authorized_users()
    
    def _detect_project_path(self) -> Path:
        """Auto-detect project root path based on current working directory.
        
        Returns:
            Path object pointing to project root
        """
        current_path = Path.cwd()
        
        # Look for common project indicators
        project_indicators = [
            "main.py", "requirements.txt", ".git", 
            "config", "handlers", "core"
        ]
        
        # Start from current directory and walk up
        for path in [current_path] + list(current_path.parents):
            if any((path / indicator).exists() for indicator in project_indicators):
                logger.info(f"Detected project path: {path}")
                return path
        
        # Fallback to current working directory
        logger.warning("Could not detect project path, using current directory")
        return current_path
    
    def _detect_tmux_session(self) -> str:
        """Auto-detect tmux session name from environment or use default.
        
        Returns:
            Tmux session name
        """
        # Check environment variable first
        env_session = os.getenv("TMUX_SESSION_NAME")
        if env_session:
            return env_session
        
        # Check if running inside tmux
        tmux_var = os.getenv("TMUX")
        if tmux_var:
            try:
                # Extract session name from TMUX variable
                session_id = tmux_var.split(",")[1]
                return f"alya-bot-{session_id}"
            except (IndexError, ValueError):
                pass
        
        # Default fallback
        return "alya-bot"
    
    def _load_authorized_users(self) -> List[int]:
        """Load authorized user IDs from environment or config.
        
        Returns:
            List of authorized Telegram user IDs
        """
        # Try to load from environment variable
        env_users = os.getenv("ADMIN_IDS", "")
        if env_users:
            try:
                return [int(uid.strip()) for uid in env_users.split(",") if uid.strip()]
            except ValueError:
                logger.warning("Invalid ADMIN_USER_IDS format in environment")
        
        # Try to load from config file
        config_path = self.project_path / "config" / "admin_users.txt"
        if config_path.exists():
            try:
                with open(config_path, 'r') as f:
                    return [int(line.strip()) for line in f if line.strip().isdigit()]
            except (ValueError, OSError):
                logger.warning(f"Could not load admin users from {config_path}")
        
        # Fallback to empty list (no admin access)
        logger.warning("No authorized users configured. Admin functions disabled.")
        return []
    
    async def update_handler(self, update: Update, context: CallbackContext) -> None:
        """Handle /update command for bot deployment.
        
        Usage:
            /update - Update from main branch
            /update develop - Update from develop branch
            /update feature/new-feature - Update from specific feature branch
        
        Args:
            update: Telegram update object
            context: Callback context
        """
        user_id = update.effective_user.id
        username = update.effective_user.first_name
        
        # Security check - only allow authorized users
        if not self._is_authorized_user(user_id):
            await update.message.reply_text(
                f"Ara ara~ <b>{html.escape(username)}</b>-kun tidak punya izin untuk melakukan update sistem! 😤",
                parse_mode=ParseMode.HTML
            )
            return
        
        # Parse branch from command arguments
        args = context.args
        branch = args[0] if args else "main"
        
        # Validate branch name
        if not self._is_valid_branch_name(branch):
            await update.message.reply_text(
                f"Branch name tidak valid! что?! 😳\n\n"
                f"Gunakan: <code>/update [branch-name]</code>",
                parse_mode=ParseMode.HTML
            )
            return
        
        await update.message.reply_text(
            f"Alya sedang mempersiapkan update sistem dari branch <code>{html.escape(branch)}</code>... 💫",
            parse_mode=ParseMode.HTML
        )
        
        try:
            # Step 1: Git operations
            git_result = await self._perform_git_update(branch)
            
            if not git_result["success"]:
                error_msg = html.escape(git_result.get("error", "Unknown error"))
                await update.message.reply_text(
                    f"Git update gagal! что?! 😳\n\n"
                    f"Error: <code>{error_msg}</code>",
                    parse_mode=ParseMode.HTML
                )
                return
            
            # Step 2: Generate commit log
            commit_log = await self._generate_commit_log_html()
            
            # Step 3: Restart bot via tmux
            restart_result = await self._restart_bot_tmux()
            
            # Step 4: Send status message
            await self._send_update_status_html(
                update, branch, restart_result, commit_log, git_result
            )
            
        except Exception as e:
            logger.error(f"Deployment update failed: {e}")
            error_msg = html.escape(str(e))
            await update.message.reply_text(
                f"Update sistem error! дурак система! 😤\n\n"
                f"Error: <code>{error_msg}</code>",
                parse_mode=ParseMode.HTML
            )
    
    async def status_handler(self, update: Update, context: CallbackContext) -> None:
        """Handle /status command for deployment status check.
        
        Args:
            update: Telegram update object
            context: Callback context
        """
        try:
            # Check tmux session
            tmux_status = await self._check_tmux_status()
            
            # Check git status
            git_status = await self._check_git_status()
            
            # Get current branch
            current_branch = await self._get_current_branch()
            
            # Get project info
            project_info = self._get_project_info_html()
            
            # Format status message
            status_lines = [
                "🔍 <b>Status Sistem Alya Bot</b>",
                f"📁 Project Path: <code>{html.escape(str(self.project_path))}</code>",
                f"📂 Current Branch: <code>{html.escape(current_branch or 'Unknown')}</code>",
                f"📊 Git Status: {git_status['message']}",
                f"🖥️ Tmux Session: {tmux_status['message']} (<code>{html.escape(self.tmux_session)}</code>)",
                f"👥 Admin Users: {len(self.authorized_users)} configured",
                f"⏰ Checked at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            ]
            
            if project_info:
                status_lines.insert(2, project_info)
            
            if git_status.get("modified_files"):
                status_lines.append("\n📝 <b>Modified Files:</b>")
                for file_path in git_status["modified_files"][:5]:  # Show max 5 files
                    status_lines.append(f"• <code>{html.escape(file_path)}</code>")
            
            await update.message.reply_text(
                '\n'.join(status_lines),
                parse_mode=ParseMode.HTML
            )
            
        except Exception as e:
            logger.error(f"Status check failed: {e}")
            error_msg = html.escape(str(e))
            await update.message.reply_text(
                f"Error checking status! дурак система! 😤\n\n"
                f"Error: <code>{error_msg}</code>",
                parse_mode=ParseMode.HTML
            )
    
    async def restart_handler(self, update: Update, context: CallbackContext) -> None:
        """Handle /restart command for quick bot restart without git pull.
        
        Args:
            update: Telegram update object
            context: Callback context
        """
        user_id = update.effective_user.id
        username = update.effective_user.first_name
        
        # Security check
        if not self._is_authorized_user(user_id):
            await update.message.reply_text(
                f"Ara ara~ <b>{html.escape(username)}</b>-kun tidak punya izin untuk restart sistem! 😤",
                parse_mode=ParseMode.HTML
            )
            return
        
        try:
            result = await self._restart_bot_tmux()
            
            if result["success"]:
                await update.message.reply_text(
                    f"✨ Bot berhasil direstart! ✨\n\n"
                    f"🔄 Tmux session: <code>{html.escape(self.tmux_session)}</code>\n"
                    f"📁 Project path: <code>{html.escape(str(self.project_path))}</code>\n"
                    f"⏰ Restart time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                    parse_mode=ParseMode.HTML
                )
            else:
                error_msg = html.escape(result.get("error", "Unknown error"))
                await update.message.reply_text(
                    f"❌ Restart gagal! что?! 😳\n\n"
                    f"Error: <code>{error_msg}</code>",
                    parse_mode=ParseMode.HTML
                )
                
        except Exception as e:
            logger.error(f"Restart failed: {e}")
            error_msg = html.escape(str(e))
            await update.message.reply_text(
                f"Restart error! дурак система! 😤\n\n"
                f"Error: <code>{error_msg}</code>",
                parse_mode=ParseMode.HTML
            )
    
    def _get_project_info(self) -> Optional[str]:
        """Get project information from common files.
        
        Returns:
            Project name or description if found
        """
        # Try to get project name from setup.py, pyproject.toml, or package.json
        info_files = [
            ("setup.py", "name"),
            ("pyproject.toml", "name"),
            ("package.json", "name"),
            ("README.md", "title")
        ]
        
        for filename, _ in info_files:
            file_path = self.project_path / filename
            if file_path.exists():
                try:
                    content = file_path.read_text(encoding='utf-8')
                    if "alya" in content.lower() or "telegram" in content.lower():
                        return f"`{self._escape_markdown(filename)}` detected"
                except (OSError, UnicodeDecodeError):
                    continue
        
        return None
    
    async def _perform_git_update(self, branch: str) -> Dict[str, any]:
        """Perform git checkout and pull operations.
        
        Args:
            branch: Target branch to checkout and pull
            
        Returns:
            Dictionary with success status and error message if failed
        """
        try:
            # Git fetch first to get latest refs
            fetch_result = await self._run_git_command(["git", "fetch", "--all"])
            
            if not fetch_result["success"]:
                return {
                    "success": False,
                    "error": f"Fetch failed: {fetch_result['error']}"
                }
            
            # Git checkout
            checkout_result = await self._run_git_command(["git", "checkout", branch])
            
            if not checkout_result["success"]:
                return {
                    "success": False,
                    "error": f"Checkout failed: {checkout_result['error']}"
                }
            
            # Git pull
            pull_result = await self._run_git_command(["git", "pull", "origin", branch])
            
            if not pull_result["success"]:
                return {
                    "success": False,
                    "error": f"Pull failed: {pull_result['error']}"
                }
            
            return {
                "success": True,
                "fetch_output": fetch_result["output"],
                "checkout_output": checkout_result["output"],
                "pull_output": pull_result["output"]
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _generate_commit_log(self) -> str:
        """Generate formatted commit log for Telegram message.
        
        Returns:
            Formatted commit log in MarkdownV2
        """
        try:
            log_result = await self._run_git_command([
                "git", "log", f"--max-count={self.max_commit_display}", 
                "--pretty=format:%h|%an|%s|%ar"
            ])
            
            if not log_result["success"]:
                return "❌ Gagal mengambil commit log"
            
            commits = log_result["output"].strip().split('\n')
            
            if not commits or commits == ['']:
                return "📝 Tidak ada commit terbaru"
            
            commit_lines = ["🔄 *Recent Commits:*\n"]
            
            for commit in commits[:self.max_commit_display]:
                if not commit.strip():
                    continue
                    
                parts = commit.split('|')
                if len(parts) >= 4:
                    hash_short = parts[0]
                    author = parts[1]
                    message = parts[2]
                    time_ago = parts[3]
                    
                    # Truncate long commit messages
                    if len(message) > 50:
                        message = message[:47] + "..."
                    
                    # Escape special characters for MarkdownV2
                    hash_escaped = self._escape_markdown(hash_short)
                    author_escaped = self._escape_markdown(author)
                    message_escaped = self._escape_markdown(message)
                    time_escaped = self._escape_markdown(time_ago)
                    
                    commit_lines.append(
                        f"`{hash_escaped}` *{author_escaped}*\n"
                        f"└─ {message_escaped}\n"
                        f"   _{time_escaped}_\n"
                    )
            
            return '\n'.join(commit_lines)
            
        except Exception as e:
            logger.error(f"Failed to generate commit log: {e}")
            return f"❌ Error generating commit log: `{self._escape_markdown(str(e))}`"
    
    async def _restart_bot_tmux(self) -> Dict[str, any]:
        """Restart bot via tmux session.
        
        Returns:
            Dictionary with success status and error message if failed
        """
        try:
            # Check if tmux session exists
            session_check = await self._run_tmux_command([
                "tmux", "has-session", "-t", self.tmux_session
            ])
            
            if not session_check["success"]:
                return {
                    "success": False,
                    "error": f"Tmux session '{self.tmux_session}' not found"
                }
            
            # Send Ctrl+C to stop current process
            stop_result = await self._run_tmux_command([
                "tmux", "send-keys", "-t", self.tmux_session, "C-c"
            ])
            
            if not stop_result["success"]:
                return {
                    "success": False,
                    "error": f"Failed to stop bot: {stop_result['error']}"
                }
            
            # Wait a moment for graceful shutdown
            await asyncio.sleep(3)
            
            # Start bot again
            start_result = await self._run_tmux_command([
                "tmux", "send-keys", "-t", self.tmux_session, 
                "python main.py", "Enter"
            ])
            
            if not start_result["success"]:
                return {
                    "success": False,
                    "error": f"Failed to start bot: {start_result['error']}"
                }
            
            return {"success": True}
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _run_git_command(self, command: List[str]) -> Dict[str, any]:
        """Run git command asynchronously in project directory.
        
        Args:
            command: Git command as list
            
        Returns:
            Dictionary with success status, output, and error
        """
        try:
            process = await asyncio.create_subprocess_exec(
                *command,
                cwd=self.project_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0:
                return {
                    "success": True,
                    "output": stdout.decode('utf-8', errors='ignore'),
                    "error": None
                }
            else:
                return {
                    "success": False,
                    "output": stdout.decode('utf-8', errors='ignore'),
                    "error": stderr.decode('utf-8', errors='ignore')
                }
                
        except Exception as e:
            return {
                "success": False,
                "output": "",
                "error": str(e)
            }
    
    async def _run_tmux_command(self, command: List[str]) -> Dict[str, any]:
        """Run tmux command asynchronously.
        
        Args:
            command: Tmux command as list
            
        Returns:
            Dictionary with success status and error
        """
        try:
            process = await asyncio.create_subprocess_exec(
                *command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0:
                return {"success": True, "error": None}
            else:
                return {
                    "success": False,
                    "error": stderr.decode('utf-8', errors='ignore')
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _check_tmux_status(self) -> Dict[str, str]:
        """Check tmux session status.
        
        Returns:
            Dictionary with status message
        """
        try:
            tmux_check = await asyncio.create_subprocess_exec(
                "tmux", "list-sessions",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            tmux_stdout, tmux_stderr = await tmux_check.communicate()
            
            tmux_sessions = tmux_stdout.decode().strip()
            
            if self.tmux_session in tmux_sessions:
                return {"message": "Active"}
            else:
                return {"message": "Not found"}
                
        except Exception:
            return {"message": "Error checking tmux"}
    
    async def _check_git_status(self) -> Dict[str, any]:
        """Check git repository status.
        
        Returns:
            Dictionary with git status information
        """
        try:
            git_check = await asyncio.create_subprocess_exec(
                "git", "status", "--porcelain",
                cwd=self.project_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            git_stdout, git_stderr = await git_check.communicate()
            
            git_status = git_stdout.decode().strip()
            
            if not git_status:
                return {"message": "Clean", "modified_files": []}
            else:
                modified_files = [line.strip()[3:] for line in git_status.split('\n') if line.strip()]
                return {
                    "message": "Modified files detected", 
                    "modified_files": modified_files
                }
                
        except Exception:
            return {"message": "Error checking git", "modified_files": []}
    
    async def _get_current_branch(self) -> Optional[str]:
        """Get current git branch.
        
        Returns:
            Current branch name or None if error
        """
        try:
            branch_check = await asyncio.create_subprocess_exec(
                "git", "branch", "--show-current",
                cwd=self.project_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            branch_stdout, branch_stderr = await branch_check.communicate()
            
            return branch_stdout.decode().strip()
            
        except Exception:
            return None
    
    async def _send_update_status(self, update: Update, branch: str, 
                                restart_result: Dict[str, any], commit_log: str,
                                git_result: Dict[str, any]) -> None:
        """Send update status message to user.
        
        Args:
            update: Telegram update object
            branch: Git branch name
            restart_result: Result from bot restart
            commit_log: Formatted commit log
            git_result: Result from git operations
        """
        # Pre-escape all strings yang akan dipakai di f-string untuk menghindari
        # backslash di dalam expression f-string (tidak didukung di Python 3.6)
        safe_branch = self._escape_markdown(branch)
        safe_path = self._escape_markdown(str(self.project_path))
        safe_session = self._escape_markdown(self.tmux_session)
        date_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        safe_date = self._escape_markdown(date_time)
        
        if restart_result["success"]:
            status_message = (
                "✨ *Update berhasil\\!* ✨\n\n"
                f"📂 Branch: `{safe_branch}`\n"
                f"📁 Path: `{safe_path}`\n"
                f"🔄 Bot direstart via tmux: `{safe_session}`\n"
                f"⏰ Waktu: {safe_date}\n\n"
                f"{commit_log}"
            )
        else:
            error_msg = self._escape_markdown(restart_result.get("error", "Unknown error"))
            # Buat tmux commands secara terpisah untuk menghindari backslash dalam f-string
            tmux_cmd1 = "tmux send-keys -t " + self.tmux_session + " C-c"
            tmux_cmd2 = "tmux send-keys -t " + self.tmux_session + " 'python main.py' Enter"
            safe_cmd1 = self._escape_markdown(tmux_cmd1)
            safe_cmd2 = self._escape_markdown(tmux_cmd2)
            
            status_message = (
                "⚠️ *Update git berhasil, tapi restart gagal\\!* ⚠️\n\n"
                f"📂 Branch: `{safe_branch}`\n"
                f"📁 Path: `{safe_path}`\n"
                f"❌ Tmux error: `{error_msg}`\n\n"
                f"{commit_log}\n\n"
                "_Silakan restart manual dengan:_\n"
                f"`{safe_cmd1}`\n"
                f"`{safe_cmd2}`"
            )
        
        await update.message.reply_text(
            status_message,
            parse_mode=ParseMode.MARKDOWN_V2
        )
    
    async def _send_update_status_html(self, update: Update, branch: str, 
                                restart_result: Dict[str, any], commit_log: str,
                                git_result: Dict[str, any]) -> None:
        """Send update status message to user in HTML format."""
        if restart_result["success"]:
            status_message = (
                "✨ <b>Update berhasil!</b> ✨<br><br>"
                f"📂 Branch: <code>{html.escape(branch)}</code><br>"
                f"📁 Path: <code>{html.escape(str(self.project_path))}</code><br>"
                f"🔄 Bot direstart via tmux: <code>{html.escape(self.tmux_session)}</code><br>"
                f"⏰ Waktu: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}<br><br>"
                f"{commit_log}"
            )
        else:
            error_msg = html.escape(restart_result.get("error", "Unknown error"))
            status_message = (
                "⚠️ <b>Update git berhasil, tapi restart gagal!</b> ⚠️<br><br>"
                f"📂 Branch: <code>{html.escape(branch)}</code><br>"
                f"📁 Path: <code>{html.escape(str(self.project_path))}</code><br>"
                f"❌ Tmux error: <code>{error_msg}</code><br><br>"
                f"{commit_log}<br><br>"
                f"<i>Silakan restart manual dengan:</i><br>"
                f"<code>tmux send-keys -t {html.escape(self.tmux_session)} C-c</code><br>"
                f"<code>tmux send-keys -t {html.escape(self.tmux_session)} 'python main.py' Enter</code>"
            )
        
        await update.message.reply_text(
            status_message,
            parse_mode=ParseMode.HTML
        )
    
    def _is_authorized_user(self, user_id: int) -> bool:
        """Check if user is authorized to perform admin operations.
        
        Args:
            user_id: Telegram user ID
            
        Returns:
            True if user is authorized
        """
        return user_id in self.authorized_users
    
    def _is_valid_branch_name(self, branch: str) -> bool:
        """Validate git branch name.
        
        Args:
            branch: Branch name to validate
            
        Returns:
            True if branch name is valid
        """
        if not branch or len(branch) > 50:
            return False
        
        # Allow alphanumeric, hyphens, underscores, and slashes
        allowed_chars = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_/")
        return all(char in allowed_chars for char in branch)
    
    def _escape_markdown(self, text: str) -> str:
        """Escape special characters for MarkdownV2.
        
        Args:
            text: Text to escape
            
        Returns:
            Escaped text safe for MarkdownV2
        """
        if not text:
            return ""
            
        special_chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
        
        for char in special_chars:
            text = text.replace(char, f'\\{char}')
            
        return text
    
    def _get_project_info_html(self) -> Optional[str]:
        """Get project information from common files in HTML format."""
        # Try to get project name from setup.py, pyproject.toml, or package.json
        info_files = [
            ("setup.py", "name"),
            ("pyproject.toml", "name"),
            ("package.json", "name"),
            ("README.md", "title")
        ]
        
        for filename, _ in info_files:
            file_path = self.project_path / filename
            if file_path.exists():
                try:
                    content = file_path.read_text(encoding='utf-8')
                    if "alya" in content.lower() or "telegram" in content.lower():
                        return f"📦 Project: <code>{html.escape(filename)}</code> detected"
                except (OSError, UnicodeDecodeError):
                    continue
        
        return None
    
    async def _generate_commit_log_html(self) -> str:
        """Generate formatted commit log for Telegram message in HTML."""
        try:
            log_result = await self._run_git_command([
                "git", "log", f"--max-count={self.max_commit_display}", 
                "--pretty=format:%h|%an|%s|%ar"
            ])
            
            if not log_result["success"]:
                return "❌ Gagal mengambil commit log"
            
            commits = log_result["output"].strip().split('\n')
            
            if not commits or commits == ['']:
                return "📝 Tidak ada commit terbaru"
            
            commit_lines = ["🔄 <b>Recent Commits:</b><br>"]
            
            for commit in commits[:self.max_commit_display]:
                if not commit.strip():
                    continue
                    
                parts = commit.split('|')
                if len(parts) >= 4:
                    hash_short = parts[0]
                    author = parts[1]
                    message = parts[2]
                    time_ago = parts[3]
                    
                    # Truncate long commit messages
                    if len(message) > 50:
                        message = message[:47] + "..."
                    
                    # Escape for HTML
                    hash_escaped = html.escape(hash_short)
                    author_escaped = html.escape(author)
                    message_escaped = html.escape(message)
                    time_escaped = html.escape(time_ago)
                    
                    commit_lines.append(
                        f"<code>{hash_escaped}</code> <b>{author_escaped}</b><br>"
                        f"└─ {message_escaped}<br>"
                        f"   <i>{time_escaped}</i><br>"
                    )
            
            return '<br>'.join(commit_lines)
            
        except Exception as e:
            logger.error(f"Failed to generate commit log: {e}")
            return f"❌ Error generating commit log: <code>{html.escape(str(e))}</code>"

def register_admin_handlers(application, tmux_session: Optional[str] = None) -> None:
    """Register admin command handlers with the application.
    
    Args:
        application: Telegram bot application instance
        tmux_session: Optional tmux session name override
    """
    admin_handler = DeploymentManager(tmux_session)
    
    # Register command handlers
    application.add_handler(CommandHandler("update", admin_handler.update_handler))
    application.add_handler(CommandHandler("status", admin_handler.status_handler))
    application.add_handler(CommandHandler("restart", admin_handler.restart_handler))
    
    logger.info(f"Admin handlers registered - Project: {admin_handler.project_path}")
    logger.info(f"Tmux session: {admin_handler.tmux_session}")
    logger.info(f"Authorized users: {len(admin_handler.authorized_users)}")