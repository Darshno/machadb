"""
nenapu.py — The Buffer Pool (Memory Cache) of MachaDB

'Nenapu' means 'memory' in Kannada. And just like your memory
before an exam, this buffer pool tries its best to hold onto
important pages but eventually forgets the old ones.

The Buffer Pool sits between the Table layer and the Pager (Notebook).
When someone asks for a page:
  1. Check if it's already in memory (cache HIT — chill macha!)
  2. If not, load it from disk (cache MISS — swalpa wait madu)
  3. If memory is full, evict the least-recently-used page
  4. If the evicted page was dirty, flush it to disk first

This is an LRU (Least Recently Used) cache — the same strategy
used by every real database. The pages you touched most recently
stay in memory. The ones you forgot about get evicted.

Like hostel rooms — use it or lose it, macha.
"""

from collections import OrderedDict
from typing import Optional

from .constants import DEFAULT_BUFFER_POOL_SIZE
from .page import Page
from .notebook import Notebook


class Nenapu:
    """
    LRU Buffer Pool — caches pages in memory to avoid disk I/O.

    This is one of the most important performance components in any
    database. Without this, every single row read would hit the disk.
    With this, hot pages stay in RAM. Smart, right?

    Uses Python's OrderedDict which maintains insertion order and
    supports move_to_end() — perfect for LRU, macha.
    """

    def __init__(self, notebook: Notebook, max_pages: int = DEFAULT_BUFFER_POOL_SIZE):
        """
        Initialize the buffer pool.

        Args:
            notebook: The underlying Pager for disk I/O.
            max_pages: Maximum number of pages to keep in memory.
                       Default is 64 pages = 256 KB.
        """
        self.notebook = notebook
        self.max_pages = max_pages
        # OrderedDict: page_id → Page (LRU order: oldest at front)
        self._cache: OrderedDict[int, Page] = OrderedDict()
        self._hit_count = 0
        self._miss_count = 0

    def get_page(self, page_number: int) -> Page:
        """
        Get a page by its number. Uses cache if available.

        This is the main entry point for all page reads.
        The Table layer calls this instead of going to Notebook directly.

        Args:
            page_number: The page to fetch.

        Returns:
            The Page object (from cache or freshly loaded from disk).
        """
        if page_number in self._cache:
            # Cache HIT — move to end (most recently used)
            self._cache.move_to_end(page_number)
            self._hit_count += 1
            return self._cache[page_number]

        # Cache MISS — load from disk
        self._miss_count += 1
        page = self.notebook.read_page(page_number)

        # Make room if cache is full
        if len(self._cache) >= self.max_pages:
            self._evict_one()

        self._cache[page_number] = page
        self._cache.move_to_end(page_number)
        return page

    def put_page(self, page: Page):
        """
        Put a page into the buffer pool (after modification).

        Marks the page as dirty so it gets flushed to disk
        when evicted or when flush_all() is called.

        Args:
            page: The modified Page object.
        """
        page.dirty = True
        page_id = page.page_id

        if page_id in self._cache:
            self._cache[page_id] = page
            self._cache.move_to_end(page_id)
        else:
            if len(self._cache) >= self.max_pages:
                self._evict_one()
            self._cache[page_id] = page
            self._cache.move_to_end(page_id)

    def new_page(self) -> Page:
        """
        Allocate a new page through the pager and add it to the pool.

        Returns:
            A fresh, empty Page ready for use.
        """
        page = self.notebook.allocate_page()

        if len(self._cache) >= self.max_pages:
            self._evict_one()

        self._cache[page.page_id] = page
        self._cache.move_to_end(page.page_id)
        return page

    def _evict_one(self):
        """
        Evict the least-recently-used page from the cache.

        If the page is dirty (modified), flush it to disk first.
        We're not savages, macha — we don't just throw away data.
        """
        if not self._cache:
            return

        # Pop the oldest item (front of OrderedDict)
        page_id, page = self._cache.popitem(last=False)

        if page.dirty:
            self.notebook.write_page(page)

    def flush_page(self, page_number: int):
        """
        Flush a specific dirty page to disk.

        Args:
            page_number: The page to flush.
        """
        if page_number in self._cache:
            page = self._cache[page_number]
            if page.dirty:
                self.notebook.write_page(page)
                page.dirty = False

    def flush_all(self):
        """
        Flush ALL dirty pages to disk.

        Called during:
          - COMMIT (pakka)
          - Database close
          - Checkpoint
          - When you're scared data might get lost at 3 AM
        """
        for page_id, page in self._cache.items():
            if page.dirty:
                self.notebook.write_page(page)
                page.dirty = False
        self.notebook.sync()

    def invalidate(self, page_number: int):
        """
        Remove a page from the cache without flushing.

        Use with caution, macha — you'll lose any dirty changes!
        This is mainly for recovery/rollback scenarios.
        """
        if page_number in self._cache:
            del self._cache[page_number]

    def invalidate_all(self):
        """Clear the entire cache. Nuclear option, boss."""
        # Flush dirty pages first — we're responsible engineers (sometimes)
        self.flush_all()
        self._cache.clear()

    @property
    def size(self) -> int:
        """Number of pages currently in the cache."""
        return len(self._cache)

    @property
    def hit_rate(self) -> float:
        """Cache hit rate as a percentage. Higher = better performance."""
        total = self._hit_count + self._miss_count
        if total == 0:
            return 0.0
        return (self._hit_count / total) * 100.0

    @property
    def stats(self) -> dict:
        """Get buffer pool statistics for debugging."""
        return {
            "cached_pages": len(self._cache),
            "max_pages": self.max_pages,
            "hits": self._hit_count,
            "misses": self._miss_count,
            "hit_rate": f"{self.hit_rate:.1f}%",
            "dirty_pages": sum(1 for p in self._cache.values() if p.dirty),
            "mood": "chill" if self.hit_rate > 80 else "swalpa tension",
        }

    def close(self):
        """Flush everything and release resources."""
        self.flush_all()
        self._cache.clear()

    def __repr__(self) -> str:
        return (
            f"Nenapu(cached={len(self._cache)}/{self.max_pages}, "
            f"hit_rate={self.hit_rate:.1f}%)"
        )
