"""RAG (Retrieval-Augmented Generation) management for henzai.

Handles document indexing, vector database management, and integration
with Ramalama's native RAG capabilities.
"""

import logging
import subprocess
import json
import os
import time
from pathlib import Path
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, asdict
from datetime import datetime
import hashlib

logger = logging.getLogger(__name__)


@dataclass
class RAGStatus:
    """Status of RAG indexing and configuration."""
    enabled: bool
    indexed: bool
    file_count: int
    last_indexed: Optional[str]  # ISO timestamp
    format: str
    db_path: str
    source_path: str
    ocr_enabled: bool
    error: Optional[str] = None
    
    def to_json(self) -> str:
        """Convert to JSON string for D-Bus."""
        return json.dumps(asdict(self))
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'RAGStatus':
        """Create from dictionary."""
        return cls(**data)


@dataclass
class IndexResult:
    """Result of document indexing operation."""
    success: bool
    file_count: int
    error: Optional[str] = None
    duration_seconds: Optional[float] = None


class RAGManager:
    """Manages RAG document indexing and vector database."""
    
    # Supported document formats
    SUPPORTED_FORMATS = {
        '.pdf', '.docx', '.pptx', '.xlsx', 
        '.html', '.htm', '.md', '.markdown',
        '.adoc', '.asciidoc', '.txt'
    }
    
    # Supported vector database formats
    VECTOR_FORMATS = ['qdrant', 'json', 'markdown', 'milvus']
    
    def __init__(self, db_path: Optional[str] = None):
        """
        Initialize RAG manager.
        
        Args:
            db_path: Path to vector database (default: ~/.local/share/henzai/rag-db)
        """
        if db_path is None:
            db_path = os.path.expanduser('~/.local/share/henzai/rag-db')
        
        self.db_path = Path(db_path)
        self.metadata_file = self.db_path / 'metadata.json'
        
        # Create db directory if needed
        self.db_path.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Initialized RAG manager with db_path: {self.db_path}")
    
    def index_documents(
        self, 
        source_path: str, 
        format: str = "qdrant", 
        enable_ocr: bool = False,
        on_progress: Optional[callable] = None
    ) -> IndexResult:
        """
        Index documents from source_path into vector database.
        
        Args:
            source_path: Path to documents folder
            format: Vector database format (qdrant, json, markdown, milvus)
            enable_ocr: Enable OCR for PDFs with images
            on_progress: Optional callback for progress updates (message, percent)
            
        Returns:
            IndexResult with success status and details
        """
        logger.info(f"Starting RAG indexing: source={source_path}, format={format}, ocr={enable_ocr}")
        
        # Check if database already exists (either from successful or failed previous indexing)
        metadata = self._load_metadata()
        db_exists = self.db_path.exists()
        
        # Delete existing database if it exists
        # This is needed because:
        # 1. ramalama rag doesn't support --overwrite or --update
        # 2. Qdrant collection persists inside container even if host directory looks empty
        # 3. User might be re-indexing same or different source
        # TODO: Replace with incremental update once ramalama supports it
        if db_exists:
            try:
                import shutil
                shutil.rmtree(self.db_path)
                if metadata is not None and metadata.get('source_path') == source_path:
                    logger.info("Detected re-indexing of same source - removed old database")
                elif metadata is None:
                    logger.warning("Found incomplete database from previous failed indexing - removed")
                else:
                    logger.info("Switching to different source - removed old database")
            except Exception as e:
                logger.warning(f"Failed to remove existing database (continuing anyway): {e}")
        
        # Ensure directory exists for podman to mount
        self.db_path.mkdir(parents=True, exist_ok=True)
        logger.info(f"RAG database directory ready at {self.db_path}")
        
        # Validate inputs
        source_path_obj = Path(source_path)
        if not source_path_obj.exists():
            error = f"Source path does not exist: {source_path}"
            logger.error(error)
            return IndexResult(success=False, file_count=0, error=error)
        
        if format not in self.VECTOR_FORMATS:
            error = f"Unsupported format: {format}. Must be one of {self.VECTOR_FORMATS}"
            logger.error(error)
            return IndexResult(success=False, file_count=0, error=error)
        
        # Count supported files
        file_count = self._count_supported_files(source_path_obj)
        if file_count == 0:
            error = f"No supported files found in {source_path}. Supported: {self.SUPPORTED_FORMATS}"
            logger.warning(error)
            return IndexResult(success=False, file_count=0, error=error)
        
        logger.info(f"Found {file_count} supported files to index")
        if on_progress:
            on_progress(f"Found {file_count} files to index", 10)
        
        # Build ramalama rag command
        # Use full path since systemd service doesn't have ~/.local/bin in PATH
        ramalama_bin = os.path.expanduser('~/.local/bin/ramalama')
        if not Path(ramalama_bin).exists():
            ramalama_bin = '/usr/bin/ramalama'  # Fallback to system install
        
        cmd = [ramalama_bin, 'rag']
        cmd.extend(['--format', format])
        
        if enable_ocr:
            cmd.append('--ocr')
        
        cmd.append(str(source_path_obj))
        cmd.append(str(self.db_path))
        
        logger.info(f"Running command: {' '.join(cmd)}")
        
        # Run indexing
        start_time = time.time()
        
        # Send initial progress
        if on_progress:
            on_progress("Starting document indexing...", 10)
        
        try:
            # Use Popen to capture output and parse progress
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1  # Line buffered
            )
            
            # Parse output for download/indexing progress
            download_started = False
            converting_count = 0
            finished_count = 0
            for line in iter(process.stdout.readline, ''):
                if not line:
                    break
                
                line = line.strip()
                logger.debug(f"ramalama rag output: {line}")
                
                # Detect container download
                if 'Trying to pull' in line or 'Pulling' in line:
                    if not download_started:
                        download_started = True
                        if on_progress:
                            on_progress("Downloading RAG tools (~4 GB, first time only)...", 10)
                elif 'Copying blob' in line:
                    if on_progress:
                        on_progress("Downloading container layers...", 30)
                elif 'Writing manifest' in line or 'Storing signatures' in line:
                    if on_progress:
                        on_progress("Finalizing container download...", 50)
                elif 'Converting' in line and ('.md' in line or '.html' in line or '.pdf' in line or '.docx' in line):
                    # Converting individual documents
                    converting_count += 1
                    if on_progress:
                        # Show progress based on how many files we've seen
                        progress = min(50 + (converting_count * 5), 80)
                        on_progress(f"Processing document {converting_count}...", progress)
                elif 'Finished converting' in line:
                    # Document conversion finished
                    finished_count += 1
                    if on_progress:
                        progress = min(60 + (finished_count * 5), 90)
                        on_progress(f"Completed {finished_count} document(s)...", progress)
            
            # Wait for process to complete
            returncode = process.wait(timeout=3600)  # 1 hour timeout for large corpora
            
            duration = time.time() - start_time
            
            if returncode != 0:
                error = f"Indexing failed with exit code {returncode}"
                logger.error(error)
                if on_progress:
                    on_progress(f"Indexing failed", 0)
                return IndexResult(success=False, file_count=0, error=error, duration_seconds=duration)
            
            logger.info(f"Indexing completed successfully in {duration:.1f}s")
            
            if on_progress:
                on_progress("Saving metadata...", 90)
            
            # Save metadata
            metadata = {
                'version': '0.3.0',
                'format': format,
                'source_path': str(source_path_obj),
                'indexed_at': datetime.now().isoformat(),
                'file_count': file_count,
                'ocr_enabled': enable_ocr,
                'duration_seconds': duration,
                'source_hash': self._hash_directory(source_path_obj)
            }
            
            self._save_metadata(metadata)
            
            if on_progress:
                on_progress(f"Indexed {file_count} files successfully", 100)
            
            return IndexResult(
                success=True, 
                file_count=file_count, 
                duration_seconds=duration
            )
            
        except subprocess.TimeoutExpired:
            error = "Indexing timed out (> 1 hour)"
            logger.error(error)
            if on_progress:
                on_progress("Indexing timed out", 0)
            return IndexResult(success=False, file_count=0, error=error)
        
        except Exception as e:
            error = f"Indexing error: {str(e)}"
            logger.error(error, exc_info=True)
            if on_progress:
                on_progress(f"Indexing error: {str(e)}", 0)
            return IndexResult(success=False, file_count=0, error=error)
    
    def get_status(self, source_path: str = "", rag_enabled: bool = False) -> RAGStatus:
        """
        Get current RAG status.
        
        Args:
            source_path: Current configured source path
            rag_enabled: Whether RAG is enabled in settings
            
        Returns:
            RAGStatus object
        """
        metadata = self._load_metadata()
        
        if metadata is None:
            # Not indexed yet
            return RAGStatus(
                enabled=rag_enabled,
                indexed=False,
                file_count=0,
                last_indexed=None,
                format='qdrant',
                db_path=str(self.db_path),
                source_path=source_path,
                ocr_enabled=False
            )
        
        return RAGStatus(
            enabled=rag_enabled,
            indexed=True,
            file_count=metadata.get('file_count', 0),
            last_indexed=metadata.get('indexed_at'),
            format=metadata.get('format', 'qdrant'),
            db_path=str(self.db_path),
            source_path=metadata.get('source_path', source_path),
            ocr_enabled=metadata.get('ocr_enabled', False)
        )
    
    def is_indexed(self) -> bool:
        """Check if RAG database exists and is valid."""
        return self.metadata_file.exists() and self._load_metadata() is not None
    
    def needs_reindex(self, source_path: str) -> bool:
        """
        Check if documents need reindexing.
        
        Args:
            source_path: Current source path
            
        Returns:
            True if reindexing needed (source changed or doesn't exist)
        """
        if not self.is_indexed():
            return True
        
        metadata = self._load_metadata()
        if metadata is None:
            return True
        
        # Check if source path changed
        if metadata.get('source_path') != source_path:
            return True
        
        # Check if source hash changed (files added/removed/modified)
        old_hash = metadata.get('source_hash')
        new_hash = self._hash_directory(Path(source_path))
        
        return old_hash != new_hash
    
    def clear_index(self):
        """Clear the RAG index and metadata."""
        logger.info("Clearing RAG index")
        
        # Remove metadata
        if self.metadata_file.exists():
            self.metadata_file.unlink()
        
        # Remove vector database files (but keep directory)
        for item in self.db_path.iterdir():
            if item.is_file():
                item.unlink()
            elif item.is_dir() and item.name != 'metadata.json':
                # Remove subdirectories (qdrant collections, etc.)
                import shutil
                shutil.rmtree(item)
        
        logger.info("RAG index cleared")
    
    def _count_supported_files(self, path: Path) -> int:
        """Count supported document files in path."""
        count = 0
        
        if path.is_file():
            if path.suffix.lower() in self.SUPPORTED_FORMATS:
                return 1
            return 0
        
        for item in path.rglob('*'):
            if item.is_file() and item.suffix.lower() in self.SUPPORTED_FORMATS:
                count += 1
        
        return count
    
    def _hash_directory(self, path: Path) -> str:
        """
        Create hash of directory contents (file paths and mtimes).
        Used to detect if source documents changed.
        """
        if not path.exists():
            return ""
        
        hasher = hashlib.sha256()
        
        if path.is_file():
            hasher.update(str(path).encode())
            hasher.update(str(path.stat().st_mtime).encode())
            return hasher.hexdigest()
        
        # Hash all supported files (path + mtime)
        files = []
        for item in sorted(path.rglob('*')):
            if item.is_file() and item.suffix.lower() in self.SUPPORTED_FORMATS:
                files.append((str(item.relative_to(path)), item.stat().st_mtime))
        
        for file_path, mtime in files:
            hasher.update(file_path.encode())
            hasher.update(str(mtime).encode())
        
        return hasher.hexdigest()
    
    def _save_metadata(self, metadata: Dict[str, Any]):
        """Save metadata to JSON file."""
        try:
            with open(self.metadata_file, 'w') as f:
                json.dump(metadata, f, indent=2)
            logger.debug(f"Saved metadata to {self.metadata_file}")
        except Exception as e:
            logger.error(f"Failed to save metadata: {e}", exc_info=True)
    
    def _load_metadata(self) -> Optional[Dict[str, Any]]:
        """Load metadata from JSON file."""
        if not self.metadata_file.exists():
            return None
        
        try:
            with open(self.metadata_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load metadata: {e}", exc_info=True)
            return None
    
    def get_rag_flag(self) -> Optional[str]:
        """
        Get the --rag flag value for ramalama serve.
        
        Returns:
            Path to RAG database if indexed, None otherwise
        """
        if self.is_indexed():
            return str(self.db_path)
        return None
    
    def retrieve_context(self, query: str, top_k: int = 3) -> List[str]:
        """
        Retrieve relevant document chunks for a query.
        
        This is a client-side RAG implementation that reads from the indexed
        vector database and returns relevant context.
        
        Args:
            query: User's query
            top_k: Number of top results to return
            
        Returns:
            List of relevant document chunks
        """
        if not self.is_indexed():
            logger.debug("RAG not indexed, returning empty context")
            return []
        
        try:
            # Import qdrant_client locally to avoid hard dependency
            try:
                from qdrant_client import QdrantClient
                from qdrant_client.models import Distance, VectorParams
            except ImportError:
                logger.error("qdrant_client not installed. Install with: pip install qdrant-client")
                return []
            
            # Connect to local Qdrant database
            client = QdrantClient(path=str(self.db_path))
            
            # Get collection name (should be 'documents' by default)
            collections = client.get_collections()
            if not collections.collections:
                logger.warning("No collections found in Qdrant database")
                return []
            
            collection_name = collections.collections[0].name
            logger.debug(f"Using collection: {collection_name}")
            
            # For now, use simple text matching as we don't have embeddings yet
            # TODO: Add proper embedding model (e.g., sentence-transformers)
            # For basic functionality, we'll search by metadata/payload
            
            # Search using scroll (get all and filter by text similarity)
            # This is a simplified approach - proper implementation needs embeddings
            results = client.scroll(
                collection_name=collection_name,
                limit=top_k,
                with_payload=True,
                with_vectors=False
            )
            
            contexts = []
            for point in results[0]:  # results is (points, next_page_offset)
                if point.payload and 'text' in point.payload:
                    text = point.payload['text']
                    # Simple relevance check: does query appear in text?
                    if any(word.lower() in text.lower() for word in query.split() if len(word) > 3):
                        contexts.append(text)
                        if len(contexts) >= top_k:
                            break
            
            if contexts:
                logger.info(f"Retrieved {len(contexts)} RAG context chunks")
            else:
                logger.debug(f"No relevant context found for query: {query[:50]}...")
            
            return contexts
            
        except Exception as e:
            logger.error(f"Error retrieving RAG context: {e}", exc_info=True)
            return []

