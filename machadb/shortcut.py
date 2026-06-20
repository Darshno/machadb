"""
shortcut.py — The B-Tree Indexing Engine of MachaDB

'Shortcut' because instead of searching the whole city (table scan),
you take the shortcut directly to the destination (O(log n) lookup).

This is a B-Tree implementation. It's the most complex data structure
in any database. We wrote this at 4 AM after 6 cups of filter coffee.
If it works, it's a miracle.

Node Layout (in a 4096 byte page):
    [1 byte: is_leaf (0 or 1)]
    [2 bytes: num_keys]
    [4 bytes: next_leaf_page_id (0 if none)]
    [ ... keys and pointers ... ]

For simplicity, if a node overflows PAGE_SIZE, we split it.
"""

from typing import Any, List, Optional, Tuple

from .constants import PAGE_SIZE
from .page import Page
from .notebook import Notebook
from .nenapu import Nenapu
from .serializer import encode_value, decode_value
from .errors import MachaError, DataUltaError
import struct

# T is minimum degree. A node can hold up to 2T - 1 keys.
# We set it conservatively so variable length strings don't overflow 4KB.
# 50 means up to 99 keys per node.
B_TREE_DEGREE = 50 


class BTreeNode:
    """A single node in the B-Tree, backed by a Page."""
    def __init__(self, page_id: int, is_leaf: bool = True):
        self.page_id = page_id
        self.is_leaf = is_leaf
        self.keys: List[Any] = []
        self.row_ptrs: List[Tuple[int, int]] = []  # (page_id, slot_idx)
        self.children: List[int] = []  # child page_ids
        self.next_leaf: int = 0
        self.dirty = False

    def to_bytes(self) -> bytes:
        """Serialize this node into a 4096-byte buffer."""
        buffer = bytearray()
        
        # Header
        buffer.extend(struct.pack(">bHI", self.is_leaf, len(self.keys), self.next_leaf))
        
        # Keys and Row Pointers
        for i in range(len(self.keys)):
            encoded_key = encode_value(self.keys[i])
            # To know the length of the key during decode, encode_value already puts lengths
            # for strings. But wait, encode_value puts type tag, and string has 4-byte length.
            # So decode_value handles it perfectly!
            buffer.extend(encoded_key)
            
            ptr_page, ptr_slot = self.row_ptrs[i]
            buffer.extend(struct.pack(">IH", ptr_page, ptr_slot))
            
        # Children (if internal node)
        if not self.is_leaf:
            for child_id in self.children:
                buffer.extend(struct.pack(">I", child_id))
                
        if len(buffer) > PAGE_SIZE:
            raise DataUltaError(f"macha! B-Tree node too big ({len(buffer)} bytes)! Decrease B_TREE_DEGREE.")
            
        # Pad to PAGE_SIZE
        buffer.extend(b"\x00" * (PAGE_SIZE - len(buffer)))
        return bytes(buffer)

    @classmethod
    def from_bytes(cls, data: bytes, page_id: int) -> "BTreeNode":
        """Deserialize a node from a page."""
        is_leaf, num_keys, next_leaf = struct.unpack_from(">bHI", data, 0)
        node = cls(page_id, bool(is_leaf))
        node.next_leaf = next_leaf
        
        offset = 7
        for _ in range(num_keys):
            key, offset = decode_value(data, offset)
            node.keys.append(key)
            
            ptr_page, ptr_slot = struct.unpack_from(">IH", data, offset)
            node.row_ptrs.append((ptr_page, ptr_slot))
            offset += 6
            
        if not node.is_leaf:
            for _ in range(num_keys + 1):
                child_id = struct.unpack_from(">I", data, offset)[0]
                node.children.append(child_id)
                offset += 4
                
        return node


class Shortcut:
    """
    The B-Tree Index Manager.
    Maps an indexed key to a row pointer: (page_id, slot_idx)
    """
    def __init__(self, filepath: str):
        self.notebook = Notebook(filepath)
        self.pool = Nenapu(self.notebook)
        
        # Root is always page 0. If file is new, create root.
        if self.notebook.total_pages == 1:
            # Pager created a generic page 0 file header.
            # We override page 1 as the BTree root.
            root_page = self.pool.new_page()
            root_node = BTreeNode(root_page.page_id, is_leaf=True)
            self._save_node(root_node)
            self.root_page_id = root_page.page_id
        else:
            self.root_page_id = 1

    def _load_node(self, page_id: int) -> BTreeNode:
        page = self.pool.get_page(page_id)
        return BTreeNode.from_bytes(page.data, page_id)

    def _save_node(self, node: BTreeNode):
        page = self.pool.get_page(node.page_id)
        page.data = bytearray(node.to_bytes())
        self.pool.put_page(page)

    def _new_node(self, is_leaf: bool = True) -> BTreeNode:
        page = self.pool.new_page()
        node = BTreeNode(page.page_id, is_leaf=is_leaf)
        return node

    def search(self, key: Any) -> List[Tuple[int, int]]:
        """
        Find row pointers for a given key.
        Returns a list because indexes can have duplicates.
        """
        return self._search_node(self.root_page_id, key)

    def _search_node(self, node_id: int, key: Any) -> List[Tuple[int, int]]:
        node = self._load_node(node_id)
        
        i = 0
        while i < len(node.keys) and key > node.keys[i]:
            i += 1
            
        results = []
        
        # If we found matches in this node, collect them
        if i < len(node.keys) and key == node.keys[i]:
            # Collect all duplicates in this node
            j = i
            while j < len(node.keys) and key == node.keys[j]:
                results.append(node.row_ptrs[j])
                j += 1
                
        # If leaf, we are done
        if node.is_leaf:
            return results
            
        # For internal nodes, we must also search the children
        # if the key could be distributed there (handling duplicates)
        if i < len(node.keys) and key == node.keys[i]:
            # Key matches, search left child and right child
            results.extend(self._search_node(node.children[i], key))
            results.extend(self._search_node(node.children[i+1], key))
        else:
            # Key not found here, just go to the correct child
            results.extend(self._search_node(node.children[i], key))
            
        return results

    def insert(self, key: Any, row_ptr: Tuple[int, int]):
        """Insert a new key -> row_ptr mapping."""
        root = self._load_node(self.root_page_id)
        
        if len(root.keys) >= 2 * B_TREE_DEGREE - 1:
            # Root is full, split it
            new_root = self._new_node(is_leaf=False)
            new_root.children.append(self.root_page_id)
            self._split_child(new_root, 0, root)
            self.root_page_id = new_root.page_id
            self._insert_non_full(new_root, key, row_ptr)
        else:
            self._insert_non_full(root, key, row_ptr)

    def _split_child(self, parent: BTreeNode, i: int, child: BTreeNode):
        """Split a full child node during insert."""
        new_node = self._new_node(is_leaf=child.is_leaf)
        
        # Move upper half to new node
        median_idx = B_TREE_DEGREE - 1
        
        new_node.keys = child.keys[median_idx+1:]
        new_node.row_ptrs = child.row_ptrs[median_idx+1:]
        
        if not child.is_leaf:
            new_node.children = child.children[median_idx+1:]
            child.children = child.children[:median_idx+1]
            
        # Median goes up to parent
        up_key = child.keys[median_idx]
        up_ptr = child.row_ptrs[median_idx]
        
        child.keys = child.keys[:median_idx]
        child.row_ptrs = child.row_ptrs[:median_idx]
        
        # Link leaves
        if child.is_leaf:
            new_node.next_leaf = child.next_leaf
            child.next_leaf = new_node.page_id
            
        # Insert median into parent
        parent.keys.insert(i, up_key)
        parent.row_ptrs.insert(i, up_ptr)
        parent.children.insert(i+1, new_node.page_id)
        
        self._save_node(child)
        self._save_node(new_node)
        self._save_node(parent)

    def _insert_non_full(self, node: BTreeNode, key: Any, row_ptr: Tuple[int, int]):
        """Insert into a node that is guaranteed not to be full."""
        i = len(node.keys) - 1
        
        if node.is_leaf:
            # Find position and insert
            node.keys.append(None)
            node.row_ptrs.append(None)
            while i >= 0 and key < node.keys[i]:
                node.keys[i+1] = node.keys[i]
                node.row_ptrs[i+1] = node.row_ptrs[i]
                i -= 1
            node.keys[i+1] = key
            node.row_ptrs[i+1] = row_ptr
            self._save_node(node)
        else:
            while i >= 0 and key < node.keys[i]:
                i -= 1
            i += 1
            
            child = self._load_node(node.children[i])
            if len(child.keys) >= 2 * B_TREE_DEGREE - 1:
                self._split_child(node, i, child)
                if key > node.keys[i]:
                    i += 1
                child = self._load_node(node.children[i])
                
            self._insert_non_full(child, key, row_ptr)

    def delete(self, key: Any, row_ptr: Tuple[int, int]):
        """
        Delete a specific mapping.
        B-Tree deletes are famously painful. Since this is MachaDB,
        we just leave tombstones or ignore it for now.
        (Full B-Tree delete requires merging nodes).
        
        For now, we'll just remove it if it's in a leaf, without merging.
        It's called the "lazy engineering student" approach.
        """
        self._lazy_delete(self.root_page_id, key, row_ptr)

    def _lazy_delete(self, node_id: int, key: Any, row_ptr: Tuple[int, int]) -> bool:
        node = self._load_node(node_id)
        
        found = False
        for i in range(len(node.keys)):
            if node.keys[i] == key and node.row_ptrs[i] == row_ptr:
                # Remove it
                node.keys.pop(i)
                node.row_ptrs.pop(i)
                self._save_node(node)
                found = True
                break
                
        if not node.is_leaf and not found:
            i = 0
            while i < len(node.keys) and key > node.keys[i]:
                i += 1
            # Search children
            if i < len(node.keys) and key == node.keys[i]:
                found = self._lazy_delete(node.children[i], key, row_ptr) or \
                        self._lazy_delete(node.children[i+1], key, row_ptr)
            else:
                found = self._lazy_delete(node.children[i], key, row_ptr)
                
        return found

    def flush(self):
        self.pool.flush_all()

    def close(self):
        self.pool.close()
        self.notebook.close()
