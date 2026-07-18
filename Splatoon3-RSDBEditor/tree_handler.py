from PyQt6.QtWidgets import QTreeWidgetItem, QApplication
from PyQt6.QtGui import QFont, QBrush, QColor
from PyQt6.QtCore import Qt
import byml
import time

CHUNK_SIZE = 500

class TreeHandler:
    @staticmethod
    def populate_tree(tree_w, data, auto_expand=False, progress_cb=None, is_cancelled_cb=None):
        tree_w.setUpdatesEnabled(False)
        tree_w.blockSignals(True)
        tree_w.clear()
        
        root = tree_w.invisibleRootItem()
        TreeHandler.add_items(root, data, tree_w, progress_cb, is_cancelled_cb)
            
        tree_w.blockSignals(False)
        
        if auto_expand:
            TreeHandler.expand_all_safely(tree_w, is_cancelled_cb, progress_cb)
        else:
            for i in range(tree_w.topLevelItemCount()):
                if is_cancelled_cb and is_cancelled_cb(): break
                root_item = tree_w.topLevelItem(i)
                if root_item is None:
                    continue
                raw_data = root_item.data(0, Qt.ItemDataRole.UserRole + 2)
                
                child_count = len(raw_data) if isinstance(raw_data, (dict, list)) else 0
                if child_count < 1000:
                    if root_item.childCount() == 1 and root_item.child(0).text(0) == "_dummy_":
                        root_item.removeChild(root_item.child(0))
                        TreeHandler.add_items(root_item, raw_data, None, None, is_cancelled_cb)
                    root_item.setExpanded(True)
                    if root_item.text(0) == "GameParameters":
                        for j in range(root_item.childCount()):
                            if is_cancelled_cb and is_cancelled_cb(): break
                            child_j = root_item.child(j)
                            if child_j:
                                if child_j.childCount() == 1 and child_j.child(0).text(0) == "_dummy_":
                                    child_j.removeChild(child_j.child(0))
                                    raw_data_j = child_j.data(0, Qt.ItemDataRole.UserRole + 2)
                                    TreeHandler.add_items(child_j, raw_data_j, None, None, is_cancelled_cb)
                                child_j.setExpanded(True)
                        
        tree_w.setUpdatesEnabled(True)

    @staticmethod
    def expand_all_safely(tree_w, is_cancelled_cb=None, progress_cb=None):
        tree_w.setUpdatesEnabled(False)
        tree_w.blockSignals(True)
        
        stack = []
        for i in range(tree_w.topLevelItemCount() - 1, -1, -1):
            stack.append(tree_w.topLevelItem(i))
            
        count = 0
        last_update = time.time()
        
        while stack:
            if is_cancelled_cb and is_cancelled_cb():
                break

            item = stack.pop()
            if item is None: continue
            
            try:
                if item.childCount() == 1 and item.child(0).text(0) == "_dummy_":
                    item.removeChild(item.child(0))
                    raw_data = item.data(0, Qt.ItemDataRole.UserRole + 2)
                    TreeHandler.add_items(item, raw_data, None, None, is_cancelled_cb)
                
                item.setExpanded(True)
                for i in range(item.childCount() - 1, -1, -1):
                    stack.append(item.child(i))
                    
                count += 1
                
                # OPTIMISATION : Ne met à jour l'UI que tous les dixièmes de seconde pour débloquer le processeur
                if time.time() - last_update > 0.1:
                    if progress_cb: progress_cb(count, 0)
                    QApplication.processEvents()
                    last_update = time.time()
            except Exception:
                pass
                
        tree_w.blockSignals(False)
        tree_w.setUpdatesEnabled(True)

    @staticmethod
    def on_item_expanded(item):
        if item.childCount() == 1 and item.child(0).text(0) == "_dummy_":
            item.removeChild(item.child(0))
            raw_data = item.data(0, Qt.ItemDataRole.UserRole + 2)
            
            tree = item.treeWidget()
            if tree: 
                tree.setUpdatesEnabled(False)
                tree.blockSignals(True)
                
            TreeHandler.add_items(item, raw_data, tree)
            
            if tree: 
                tree.blockSignals(False)
                tree.setUpdatesEnabled(True)

    @staticmethod
    def _set_item_value(it, v):
        if v is None:
            it.setText(1, "None")
            it.setFlags(it.flags() | Qt.ItemFlag.ItemIsEditable)
            it.setData(1, Qt.ItemDataRole.UserRole, "none")
            it.setData(1, Qt.ItemDataRole.UserRole + 1, "none")
            return

        python_val = v.value if hasattr(v, 'value') else v
        original_type = type(v).__name__

        it.setFlags(it.flags() | Qt.ItemFlag.ItemIsEditable)
        it.setData(1, Qt.ItemDataRole.UserRole + 1, original_type)
        it.setData(1, Qt.ItemDataRole.UserRole + 4, v)
        
        if isinstance(python_val, bool) or original_type == 'Bool':
            it.setData(1, Qt.ItemDataRole.UserRole, "bool")
            it.setText(1, str(python_val))
        elif isinstance(python_val, int) or original_type in ['Int', 'UInt', 'Int64', 'UInt64']:
            it.setData(1, Qt.ItemDataRole.UserRole, "int")
            it.setText(1, str(python_val))
        elif isinstance(python_val, float) or original_type in ['Float', 'Double']:
            it.setData(1, Qt.ItemDataRole.UserRole, "float")
            it.setText(1, str(python_val))
        else:
            it.setData(1, Qt.ItemDataRole.UserRole, "str")
            val_str = str(python_val)
            if len(val_str) > 250:
                it.setText(1, val_str[:250] + "... (truncated)")
                it.setFlags(it.flags() & ~Qt.ItemFlag.ItemIsEditable)
            else:
                it.setText(1, val_str)

    @staticmethod
    def _setup_node(it, v, force_expand=False, is_cancelled_cb=None):
        if isinstance(v, (dict, list)):
            font = it.font(0)
            font.setBold(True)
            it.setFont(0, font)
            it.setForeground(0, QBrush(QColor("#ff9f43")))
            it.setFlags(it.flags() & ~Qt.ItemFlag.ItemIsEditable)
            
            if not v:
                it.setText(1, "{}" if isinstance(v, dict) else "[]")
                it.setForeground(1, QBrush(QColor("gray")))
                it.setData(1, Qt.ItemDataRole.UserRole, "empty_dict" if isinstance(v, dict) else "empty_list") 
            else:
                it.setData(0, Qt.ItemDataRole.UserRole + 2, v)
                if force_expand:
                    TreeHandler.add_items(it, v, tree=None, progress_cb=None, is_cancelled_cb=is_cancelled_cb, force_expand=True)
                else:
                    dummy = QTreeWidgetItem(it)
                    dummy.setText(0, "_dummy_")
        else:
            TreeHandler._set_item_value(it, v)

    @staticmethod
    def add_items(parent, value, tree=None, progress_cb=None, is_cancelled_cb=None, force_expand=False):
        last_update = time.time()
        
        if isinstance(value, dict):
            total = len(value)
            children_to_add = []
            for i, (k, v) in enumerate(value.items()):
                if is_cancelled_cb and is_cancelled_cb(): break
                it = QTreeWidgetItem()
                it.setText(0, str(k))
                TreeHandler._setup_node(it, v, force_expand=force_expand, is_cancelled_cb=is_cancelled_cb)
                children_to_add.append(it)
                
                # OPTIMISATION : Ne met à jour l'UI que tous les dixièmes de seconde pour débloquer le processeur
                if tree and time.time() - last_update > 0.1:
                    if progress_cb: progress_cb(i, total)
                    QApplication.processEvents()
                    last_update = time.time()
                    
            parent.addChildren(children_to_add)
            if progress_cb: progress_cb(total, total)
            
        elif isinstance(value, list):
            total = len(value)
            children_to_add = []
            
            if total > CHUNK_SIZE:
                for i in range(0, total, CHUNK_SIZE):
                    if is_cancelled_cb and is_cancelled_cb(): break
                    chunk = value[i:i+CHUNK_SIZE]
                    chunk_it = QTreeWidgetItem()
                    chunk_it.setText(0, f"[{i} ... {min(i+CHUNK_SIZE-1, total-1)}]")
                    chunk_it.setText(1, f"[{len(chunk)}]")
                    
                    font = chunk_it.font(0)
                    font.setBold(True)
                    chunk_it.setFont(0, font)
                    chunk_it.setForeground(0, QBrush(QColor("#00a8ff")))
                    chunk_it.setForeground(1, QBrush(QColor("gray")))
                    
                    chunk_it.setData(1, Qt.ItemDataRole.UserRole, "chunk_folder")
                    chunk_it.setData(0, Qt.ItemDataRole.UserRole + 2, chunk)
                    chunk_it.setData(0, Qt.ItemDataRole.UserRole + 3, i)
                    
                    if force_expand:
                        TreeHandler.add_items(chunk_it, chunk, tree=tree, progress_cb=progress_cb, is_cancelled_cb=is_cancelled_cb, force_expand=True)
                    else:
                        dummy = QTreeWidgetItem(chunk_it)
                        dummy.setText(0, "_dummy_")
                        
                    children_to_add.append(chunk_it)
                    
                    if tree and time.time() - last_update > 0.1:
                        if progress_cb: progress_cb(i, total)
                        QApplication.processEvents()
                        last_update = time.time()
                        
                parent.addChildren(children_to_add)
                if progress_cb: progress_cb(total, total)
            else:
                offset_data = parent.data(0, Qt.ItemDataRole.UserRole + 3)
                offset = offset_data if offset_data is not None else 0
                
                for i, v in enumerate(value):
                    if is_cancelled_cb and is_cancelled_cb(): break
                    it = QTreeWidgetItem()
                    it.setText(0, f"[{offset + i}]")
                    TreeHandler._setup_node(it, v, force_expand=force_expand, is_cancelled_cb=is_cancelled_cb)
                    children_to_add.append(it)
                    
                    if tree and time.time() - last_update > 0.1:
                        if progress_cb: progress_cb(i, total)
                        QApplication.processEvents()
                        last_update = time.time()
                        
                parent.addChildren(children_to_add)
                if progress_cb: progress_cb(total, total)

    @staticmethod
    def build_dict(item):
        if item.childCount() == 1 and item.child(0).text(0) == "_dummy_":
            return item.data(0, Qt.ItemDataRole.UserRole + 2)

        is_array = (item.childCount() > 0 and (item.child(0).text(0).startswith("[") or item.data(1, Qt.ItemDataRole.UserRole) == "chunk_folder"))
        res = [] if is_array else {}

        for i in range(item.childCount()):
            c = item.child(i)
            key = c.text(0)
            
            if c.childCount() > 0:
                val = TreeHandler.build_dict(c)
            else:
                val_type = c.data(1, Qt.ItemDataRole.UserRole)
                orig_type = c.data(1, Qt.ItemDataRole.UserRole + 1)
                val_str = c.text(1)
                
                if val_str.endswith("... (truncated)"):
                    val = c.data(1, Qt.ItemDataRole.UserRole + 4)
                else:
                    if val_type == "empty_dict": val = {}
                    elif val_type == "empty_list": val = []
                    elif val_type == "none": val = None
                    elif val_type == "int":
                        int_val = int(val_str)
                        if orig_type == 'UInt' and hasattr(byml, 'UInt'): val = byml.UInt(int_val)
                        elif orig_type == 'Int64' and hasattr(byml, 'Int64'): val = byml.Int64(int_val)
                        elif orig_type == 'UInt64' and hasattr(byml, 'UInt64'): val = byml.UInt64(int_val)
                        elif hasattr(byml, 'Int'): val = byml.Int(int_val)
                        else: val = int_val
                    elif val_type == "float":
                        float_val = float(val_str.replace(' ', '').replace(',', '.'))
                        if orig_type == 'Double' and hasattr(byml, 'Double'): val = byml.Double(float_val)
                        elif hasattr(byml, 'Float'): val = byml.Float(float_val)
                        else: val = float_val
                    elif val_type == "bool":
                        bool_val = (val_str == "True")
                        if hasattr(byml, 'Bool'): val = byml.Bool(bool_val)
                        else: val = bool_val
                    else:
                        if hasattr(byml, 'String'): val = byml.String(val_str)
                        else: val = val_str

            if is_array:
                if c.data(1, Qt.ItemDataRole.UserRole) == "chunk_folder":
                    res.extend(val)
                else:
                    res.append(val)
            else: 
                res[key] = val
                
        return res