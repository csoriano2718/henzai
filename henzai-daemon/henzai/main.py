"""henzai - AI-First GNOME Desktop Assistant

Main entry point for the henzai daemon service.
"""

import sys
import logging
from gi.repository import GLib
from .dbus_service import henzaiService
from .llm import LLMClient
from .memory import MemoryStore
from .rag import RAGManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('/tmp/henzai-daemon.log')
    ]
)

logger = logging.getLogger(__name__)


def main():
    """Main entry point for the henzai daemon."""
    logger.info("Starting henzai daemon...")
    
    try:
        # Initialize memory store
        logger.info("Initializing memory store...")
        memory = MemoryStore()
        
        # Initialize RAG manager
        logger.info("Initializing RAG manager...")
        rag = RAGManager()
        
        # Check if RAG database exists to determine initial RAG mode
        rag_enabled = rag.is_indexed()
        logger.info(f"RAG database indexed: {rag_enabled}")
        
        # Initialize LLM client (will auto-detect model from Ramalama)
        logger.info("Initializing LLM client...")
        llm = LLMClient(rag_enabled=rag_enabled)
        
        # Try to detect current model from Ramalama systemd service file
        try:
            import subprocess
            result = subprocess.run(
                ['systemctl', '--user', 'cat', 'ramalama.service'],
                capture_output=True,
                text=True,
                timeout=2
            )
            if result.returncode == 0:
                # Parse ExecStart line to get the actual model being served
                for line in result.stdout.split('\n'):
                    if 'ExecStart=' in line and 'ramalama serve' in line:
                        # Extract model from ExecStart line (last argument)
                        parts = line.split()
                        if len(parts) > 0:
                            model_arg = parts[-1]  # Last argument is usually the model
                            if 'ollama://' in model_arg or 'library/' in model_arg or ':' in model_arg:
                                detected_model = model_arg
                                llm.model = detected_model
                                logger.info(f"Detected model from ramalama.service: {detected_model}")
                                break
            else:
                logger.warning(f"Could not read ramalama.service, using default: {llm.model}")
        except Exception as e:
            logger.warning(f"Could not detect model from ramalama.service: {e}, using default: {llm.model}")
        
        # Auto-detect reasoning support and enable if available
        if llm.supports_reasoning():
            llm.reasoning_enabled = True
            logger.info(f"Reasoning mode auto-enabled for model: {llm.model}")
        else:
            llm.reasoning_enabled = False
            logger.info(f"Reasoning mode not available for model: {llm.model}")
        
        # Create and register D-Bus service IMMEDIATELY
        # Don't wait for Ramalama - the GetStatus method will handle readiness checks
        logger.info("Creating D-Bus service...")
        service = henzaiService(llm, memory, rag)
        
        logger.info("henzai daemon started successfully")
        logger.info("D-Bus service available at: org.gnome.henzai")
        logger.info("Note: Ramalama may still be loading. UI will show status updates.")
        
        # Run the main loop
        loop = GLib.MainLoop()
        loop.run()
        
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt, shutting down...")
        if 'service' in locals():
            service.cleanup()
        if 'memory' in locals():
            memory.close()
        sys.exit(0)
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()










