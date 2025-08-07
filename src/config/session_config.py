"""Session configuration management utilities."""

import json
import os
from typing import Dict, Set, Optional
import logging

logger = logging.getLogger(__name__)

CONFIG_FILENAME = ".session_files.json"


class SessionFileConfig:
    """Manages session file configuration."""
    
    def __init__(self, session_dir: str):
        """Initialize session file config.
        
        Args:
            session_dir: Session working directory
        """
        self.session_dir = session_dir
        self.config_path = os.path.join(session_dir, CONFIG_FILENAME)
        self._config: Dict[str, str] = {}
        self._load_config()
    
    def _load_config(self) -> None:
        """Load configuration from file."""
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    self._config = json.load(f)
                logger.info(f"Loaded session config with {len(self._config)} files")
            except Exception as e:
                logger.error(f"Failed to load session config: {e}")
                self._config = {}
        else:
            self._config = {}
    
    def _save_config(self) -> None:
        """Save configuration to file."""
        try:
            os.makedirs(self.session_dir, exist_ok=True)
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(self._config, f, indent=2, ensure_ascii=False)
            logger.info(f"Saved session config with {len(self._config)} files")
        except Exception as e:
            logger.error(f"Failed to save session config: {e}")
    
    def has_file(self, file_id: str) -> bool:
        """Check if file ID exists in config.
        
        Args:
            file_id: File identifier
            
        Returns:
            True if file exists, False otherwise
        """
        return file_id in self._config
    
    def get_filename(self, file_id: str) -> Optional[str]:
        """Get filename for file ID.
        
        Args:
            file_id: File identifier
            
        Returns:
            Filename if exists, None otherwise
        """
        return self._config.get(file_id)
    
    def add_file(self, file_id: str, filename: str) -> None:
        """Add file to config.
        
        Args:
            file_id: File identifier
            filename: Downloaded filename
        """
        self._config[file_id] = filename
        self._save_config()
        logger.info(f"Added file to config: {file_id} -> {filename}")
    
    def remove_file(self, file_id: str) -> None:
        """Remove file from config.
        
        Args:
            file_id: File identifier
        """
        if file_id in self._config:
            filename = self._config.pop(file_id)
            self._save_config()
            logger.info(f"Removed file from config: {file_id} -> {filename}")
    
    def get_all_files(self) -> Dict[str, str]:
        """Get all files in config.
        
        Returns:
            Dictionary mapping file IDs to filenames
        """
        return self._config.copy()
    
    def get_existing_file_ids(self) -> Set[str]:
        """Get set of existing file IDs.
        
        Returns:
            Set of file IDs
        """
        return set(self._config.keys())
    
    def clear_all_files(self) -> None:
        """Clear all files from config.
        
        This method removes all file entries from the configuration
        and saves the empty configuration to disk.
        """
        file_count = len(self._config)
        self._config.clear()
        self._save_config()
        logger.info(f"Cleared all {file_count} files from session config")