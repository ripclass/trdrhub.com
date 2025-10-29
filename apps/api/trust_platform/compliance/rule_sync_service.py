#!/usr/bin/env python3
"""
Rule Sync Service
Monitors YAML rule files for changes and automatically reloads the compliance engine.
Publishes version updates to audit logs and manages rule deployment.

Features:
- File system monitoring for rule changes
- Automatic engine reload on YAML updates
- Version control integration (Git commit/push)
- Audit logging for rule deployments
- Rollback capabilities
- Health checking and validation
"""

import logging
import os
import json
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, asdict
from enum import Enum
from threading import Thread, Lock
import hashlib

# File monitoring
try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler
    HAS_WATCHDOG = True
except ImportError:
    HAS_WATCHDOG = False
    logging.warning("Watchdog not installed. Install with: pip install watchdog")

# Import our compliance modules
from .rule_engine import RuleEngine
from .rule_linter import RuleLinter
from .compliance_integration import ComplianceIntegration

logger = logging.getLogger(__name__)


class SyncEventType(Enum):
    RULE_ADDED = "rule_added"
    RULE_MODIFIED = "rule_modified"
    RULE_DELETED = "rule_deleted"
    ENGINE_RELOADED = "engine_reloaded"
    VALIDATION_FAILED = "validation_failed"
    GIT_COMMITTED = "git_committed"
    ROLLBACK_PERFORMED = "rollback_performed"


@dataclass
class SyncEvent:
    """Represents a rule sync event"""
    event_type: SyncEventType
    timestamp: datetime
    file_path: str
    rule_ids_affected: List[str]
    success: bool
    details: str
    version_hash: Optional[str] = None
    git_commit_hash: Optional[str] = None


@dataclass
class RuleVersion:
    """Represents a versioned rule set"""
    version_id: str
    timestamp: datetime
    rule_count: int
    files_hash: str
    git_commit: Optional[str] = None
    validation_passed: bool = True
    deployed: bool = False


class RuleFileHandler(FileSystemEventHandler):
    """Handles file system events for rule files"""

    def __init__(self, sync_service: 'RuleSyncService'):
        self.sync_service = sync_service

    def on_modified(self, event):
        if event.is_directory:
            return

        file_path = Path(event.src_path)
        if file_path.suffix.lower() == '.yaml' and 'rules' in file_path.parent.name:
            logger.info(f"Rule file modified: {file_path}")
            self.sync_service._handle_file_change(file_path, SyncEventType.RULE_MODIFIED)

    def on_created(self, event):
        if event.is_directory:
            return

        file_path = Path(event.src_path)
        if file_path.suffix.lower() == '.yaml' and 'rules' in file_path.parent.name:
            logger.info(f"Rule file created: {file_path}")
            self.sync_service._handle_file_change(file_path, SyncEventType.RULE_ADDED)

    def on_deleted(self, event):
        if event.is_directory:
            return

        file_path = Path(event.src_path)
        if file_path.suffix.lower() == '.yaml' and 'rules' in file_path.parent.name:
            logger.info(f"Rule file deleted: {file_path}")
            self.sync_service._handle_file_change(file_path, SyncEventType.RULE_DELETED)


class RuleSyncService:
    """Manages rule synchronization and deployment"""

    def __init__(self, compliance_dir: Path, enable_git: bool = True):
        self.compliance_dir = compliance_dir
        self.rules_dir = compliance_dir / "rules"
        self.enable_git = enable_git

        # Initialize components
        self.rule_engine = RuleEngine()
        self.rule_linter = RuleLinter()
        self.compliance_integration = ComplianceIntegration()

        # State management
        self.sync_lock = Lock()
        self.is_running = False
        self.observer = None

        # Version tracking
        self.current_version = None
        self.version_history = []
        self.sync_events = []

        # Configuration
        self.max_events = 1000
        self.max_versions = 50
        self.auto_commit = os.getenv('RULE_AUTO_COMMIT', 'false').lower() == 'true'
        self.validation_required = True

        # Callbacks
        self.event_callbacks = []

        logger.info(f"Rule sync service initialized for {self.rules_dir}")

    def start(self):
        """Start the rule synchronization service"""
        if not HAS_WATCHDOG:
            logger.error("Watchdog not available - cannot start file monitoring")
            return False

        if self.is_running:
            logger.warning("Sync service already running")
            return True

        try:
            # Initialize current version
            self._initialize_current_version()

            # Set up file monitoring
            event_handler = RuleFileHandler(self)
            self.observer = Observer()
            self.observer.schedule(event_handler, str(self.rules_dir), recursive=True)
            self.observer.start()

            self.is_running = True
            logger.info("Rule sync service started successfully")

            # Initial engine load
            self._reload_compliance_engine()

            return True

        except Exception as e:
            logger.error(f"Failed to start sync service: {e}")
            return False

    def stop(self):
        """Stop the rule synchronization service"""
        if not self.is_running:
            return

        if self.observer:
            self.observer.stop()
            self.observer.join()

        self.is_running = False
        logger.info("Rule sync service stopped")

    def register_callback(self, callback: Callable[[SyncEvent], None]):
        """Register a callback for sync events"""
        self.event_callbacks.append(callback)

    def force_reload(self) -> bool:
        """Force reload the compliance engine"""
        return self._reload_compliance_engine()

    def get_current_version(self) -> Optional[RuleVersion]:
        """Get current rule version info"""
        return self.current_version

    def get_version_history(self) -> List[RuleVersion]:
        """Get version history"""
        return self.version_history.copy()

    def get_sync_events(self, limit: int = 100) -> List[SyncEvent]:
        """Get recent sync events"""
        return self.sync_events[-limit:]

    def rollback_to_version(self, version_id: str) -> bool:
        """Rollback to a specific version"""
        if not self.enable_git:
            logger.error("Git not enabled - cannot rollback")
            return False

        version = next((v for v in self.version_history if v.version_id == version_id), None)
        if not version or not version.git_commit:
            logger.error(f"Version {version_id} not found or no git commit")
            return False

        try:
            with self.sync_lock:
                # Git checkout to specific commit
                result = subprocess.run(
                    ['git', 'checkout', version.git_commit, '--', str(self.rules_dir)],
                    cwd=self.compliance_dir,
                    capture_output=True,
                    text=True
                )

                if result.returncode != 0:
                    logger.error(f"Git rollback failed: {result.stderr}")
                    return False

                # Reload engine
                success = self._reload_compliance_engine()

                # Log rollback event
                event = SyncEvent(
                    event_type=SyncEventType.ROLLBACK_PERFORMED,
                    timestamp=datetime.now(timezone.utc),
                    file_path=str(self.rules_dir),
                    rule_ids_affected=[],
                    success=success,
                    details=f"Rolled back to version {version_id}",
                    git_commit_hash=version.git_commit
                )

                self._add_sync_event(event)
                return success

        except Exception as e:
            logger.error(f"Rollback failed: {e}")
            return False

    def validate_current_rules(self) -> Dict[str, Any]:
        """Validate all current rule files"""
        validation_results = {
            'overall_valid': True,
            'files': {},
            'summary': {
                'total_files': 0,
                'valid_files': 0,
                'total_errors': 0,
                'total_warnings': 0
            }
        }

        rule_files = list(self.rules_dir.glob("*.yaml"))
        validation_results['summary']['total_files'] = len(rule_files)

        for rule_file in rule_files:
            try:
                errors, warnings = self.rule_linter.lint_file(rule_file)
                file_valid = len(errors) == 0

                validation_results['files'][rule_file.name] = {
                    'valid': file_valid,
                    'errors': errors,
                    'warnings': warnings
                }

                if file_valid:
                    validation_results['summary']['valid_files'] += 1
                else:
                    validation_results['overall_valid'] = False

                validation_results['summary']['total_errors'] += len(errors)
                validation_results['summary']['total_warnings'] += len(warnings)

            except Exception as e:
                validation_results['files'][rule_file.name] = {
                    'valid': False,
                    'errors': [f"Validation failed: {str(e)}"],
                    'warnings': []
                }
                validation_results['overall_valid'] = False

        return validation_results

    def get_status(self) -> Dict[str, Any]:
        """Get service status information"""
        return {
            'running': self.is_running,
            'current_version': asdict(self.current_version) if self.current_version else None,
            'rules_directory': str(self.rules_dir),
            'git_enabled': self.enable_git,
            'auto_commit': self.auto_commit,
            'total_events': len(self.sync_events),
            'total_versions': len(self.version_history),
            'engine_loaded': hasattr(self.rule_engine, 'ucp600_rules') and len(self.rule_engine.ucp600_rules) > 0,
            'validation_required': self.validation_required
        }

    def _handle_file_change(self, file_path: Path, event_type: SyncEventType):
        """Handle a rule file change"""
        if not file_path.exists() and event_type != SyncEventType.RULE_DELETED:
            return

        with self.sync_lock:
            logger.info(f"Processing {event_type.value} for {file_path}")

            # Extract affected rule IDs (if possible)
            rule_ids = []
            try:
                if file_path.exists():
                    rule_ids = self._extract_rule_ids_from_file(file_path)
            except Exception as e:
                logger.warning(f"Could not extract rule IDs from {file_path}: {e}")

            # Validate if required
            validation_passed = True
            details = f"File {event_type.value}: {file_path.name}"

            if self.validation_required and file_path.exists():
                try:
                    errors, warnings = self.rule_linter.lint_file(file_path)
                    validation_passed = len(errors) == 0

                    if not validation_passed:
                        details += f" - Validation failed: {len(errors)} errors"
                        logger.error(f"Validation failed for {file_path}: {errors}")
                    elif warnings:
                        details += f" - {len(warnings)} warnings"

                except Exception as e:
                    validation_passed = False
                    details += f" - Validation error: {str(e)}"

            # Only reload if validation passed or validation disabled
            reload_success = True
            if validation_passed or not self.validation_required:
                reload_success = self._reload_compliance_engine()
                if reload_success:
                    self._create_new_version()

            # Auto-commit if enabled and successful
            git_commit_hash = None
            if self.auto_commit and validation_passed and reload_success and self.enable_git:
                git_commit_hash = self._git_auto_commit(file_path, event_type)

            # Create sync event
            event = SyncEvent(
                event_type=event_type,
                timestamp=datetime.now(timezone.utc),
                file_path=str(file_path),
                rule_ids_affected=rule_ids,
                success=validation_passed and reload_success,
                details=details,
                version_hash=self.current_version.version_id if self.current_version else None,
                git_commit_hash=git_commit_hash
            )

            self._add_sync_event(event)

            # Trigger callbacks
            for callback in self.event_callbacks:
                try:
                    callback(event)
                except Exception as e:
                    logger.error(f"Event callback failed: {e}")

    def _reload_compliance_engine(self) -> bool:
        """Reload the compliance engine with updated rules"""
        try:
            # Create new engine instance
            new_engine = RuleEngine()

            # Test load to ensure it works
            test_document = {
                "lc_number": "TEST-001",
                "expiry_date": "2024-03-15",
                "amount": {"value": 1000.00, "currency": "USD"}
            }

            result = new_engine.validate(test_document, "pro")

            # If successful, update the integration
            self.rule_engine = new_engine
            self.compliance_integration.new_engine = new_engine

            logger.info("Compliance engine reloaded successfully")

            # Create reload event
            event = SyncEvent(
                event_type=SyncEventType.ENGINE_RELOADED,
                timestamp=datetime.now(timezone.utc),
                file_path=str(self.rules_dir),
                rule_ids_affected=[],
                success=True,
                details=f"Engine reloaded with {len(new_engine.ucp600_rules) + len(new_engine.isbp_rules) + len(new_engine.local_bd_rules)} rules"
            )

            self._add_sync_event(event)
            return True

        except Exception as e:
            logger.error(f"Failed to reload compliance engine: {e}")

            # Create failure event
            event = SyncEvent(
                event_type=SyncEventType.VALIDATION_FAILED,
                timestamp=datetime.now(timezone.utc),
                file_path=str(self.rules_dir),
                rule_ids_affected=[],
                success=False,
                details=f"Engine reload failed: {str(e)}"
            )

            self._add_sync_event(event)
            return False

    def _initialize_current_version(self):
        """Initialize the current version state"""
        files_hash = self._calculate_files_hash()
        git_commit = self._get_current_git_commit() if self.enable_git else None

        self.current_version = RuleVersion(
            version_id=files_hash[:12],
            timestamp=datetime.now(timezone.utc),
            rule_count=self._count_total_rules(),
            files_hash=files_hash,
            git_commit=git_commit,
            validation_passed=True,
            deployed=True
        )

        self.version_history.append(self.current_version)

    def _create_new_version(self):
        """Create a new version after successful changes"""
        files_hash = self._calculate_files_hash()

        # Only create new version if hash changed
        if self.current_version and self.current_version.files_hash == files_hash:
            return

        git_commit = self._get_current_git_commit() if self.enable_git else None

        new_version = RuleVersion(
            version_id=files_hash[:12],
            timestamp=datetime.now(timezone.utc),
            rule_count=self._count_total_rules(),
            files_hash=files_hash,
            git_commit=git_commit,
            validation_passed=True,
            deployed=True
        )

        self.current_version = new_version
        self.version_history.append(new_version)

        # Limit version history
        if len(self.version_history) > self.max_versions:
            self.version_history = self.version_history[-self.max_versions:]

    def _calculate_files_hash(self) -> str:
        """Calculate hash of all rule files"""
        hasher = hashlib.sha256()

        rule_files = sorted(self.rules_dir.glob("*.yaml"))
        for file_path in rule_files:
            if file_path.exists():
                with open(file_path, 'rb') as f:
                    hasher.update(f.read())

        return hasher.hexdigest()

    def _count_total_rules(self) -> int:
        """Count total number of rules across all files"""
        try:
            if hasattr(self.rule_engine, 'ucp600_rules'):
                return (len(self.rule_engine.ucp600_rules) +
                       len(self.rule_engine.isbp_rules) +
                       len(self.rule_engine.local_bd_rules))
        except:
            pass

        return 0

    def _extract_rule_ids_from_file(self, file_path: Path) -> List[str]:
        """Extract rule IDs from a YAML rule file"""
        import yaml

        rule_ids = []
        try:
            with open(file_path, 'r') as f:
                data = yaml.safe_load(f)

            if isinstance(data, dict) and 'rules' in data:
                for rule in data['rules']:
                    if isinstance(rule, dict) and 'id' in rule:
                        rule_ids.append(rule['id'])

        except Exception as e:
            logger.warning(f"Could not extract rule IDs from {file_path}: {e}")

        return rule_ids

    def _git_auto_commit(self, file_path: Path, event_type: SyncEventType) -> Optional[str]:
        """Auto-commit changes to git"""
        try:
            # Add file to git
            subprocess.run(['git', 'add', str(file_path)], cwd=self.compliance_dir, check=True)

            # Create commit message
            commit_message = f"Auto-commit: {event_type.value} in {file_path.name}\n\nTriggered by rule sync service"

            # Commit
            result = subprocess.run(
                ['git', 'commit', '-m', commit_message],
                cwd=self.compliance_dir,
                capture_output=True,
                text=True
            )

            if result.returncode == 0:
                # Get commit hash
                commit_hash = subprocess.run(
                    ['git', 'rev-parse', 'HEAD'],
                    cwd=self.compliance_dir,
                    capture_output=True,
                    text=True
                ).stdout.strip()

                logger.info(f"Auto-committed changes: {commit_hash}")

                # Create git event
                event = SyncEvent(
                    event_type=SyncEventType.GIT_COMMITTED,
                    timestamp=datetime.now(timezone.utc),
                    file_path=str(file_path),
                    rule_ids_affected=[],
                    success=True,
                    details=f"Auto-committed: {commit_message}",
                    git_commit_hash=commit_hash
                )

                self._add_sync_event(event)
                return commit_hash

        except Exception as e:
            logger.error(f"Git auto-commit failed: {e}")

        return None

    def _get_current_git_commit(self) -> Optional[str]:
        """Get current git commit hash"""
        try:
            result = subprocess.run(
                ['git', 'rev-parse', 'HEAD'],
                cwd=self.compliance_dir,
                capture_output=True,
                text=True
            )

            if result.returncode == 0:
                return result.stdout.strip()

        except Exception:
            pass

        return None

    def _add_sync_event(self, event: SyncEvent):
        """Add sync event to history"""
        self.sync_events.append(event)

        # Limit event history
        if len(self.sync_events) > self.max_events:
            self.sync_events = self.sync_events[-self.max_events:]

        logger.info(f"Sync event: {event.event_type.value} - {event.details}")


def main():
    """Demo rule sync service"""
    print("=== Rule Sync Service Demo ===")

    compliance_dir = Path(__file__).parent
    sync_service = RuleSyncService(compliance_dir, enable_git=False)

    # Register demo callback
    def on_sync_event(event: SyncEvent):
        print(f"📁 {event.event_type.value}: {event.details}")

    sync_service.register_callback(on_sync_event)

    try:
        # Start service
        if sync_service.start():
            print("✅ Sync service started - watching for file changes")
            print("Status:", sync_service.get_status())

            # Simulate some file changes for demo
            print("\nSimulating file changes...")
            time.sleep(2)

            # Force reload
            print("🔄 Forcing engine reload...")
            success = sync_service.force_reload()
            print(f"   Reload {'successful' if success else 'failed'}")

            # Show version history
            print("\n📈 Version History:")
            for version in sync_service.get_version_history():
                print(f"   {version.version_id}: {version.rule_count} rules @ {version.timestamp}")

            # Show recent events
            print("\n📋 Recent Events:")
            for event in sync_service.get_sync_events(5):
                print(f"   {event.timestamp.strftime('%H:%M:%S')} - {event.event_type.value}: {event.details}")

            print("\nPress Ctrl+C to stop...")
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                pass

        else:
            print("❌ Failed to start sync service")

    finally:
        sync_service.stop()
        print("🛑 Sync service stopped")


if __name__ == "__main__":
    main()