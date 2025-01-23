import pytest
import threading


@pytest.fixture(scope="session", autouse=True)
def cleanup_threads():
    """Cleanup any lingering threads between test sessions."""
    yield
    # Force cleanup of any remaining threads
    main_thread = threading.main_thread()
    for thread in threading.enumerate():
        if thread is not main_thread:
            thread._stop()
