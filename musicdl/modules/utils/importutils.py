'''
Function:
    Implementation of Optional Import Related Utils
Author:
    Zhenchao Jin
WeChat Official Account (微信公众号):
    Charles的皮卡丘
'''
import sys
import warnings
import importlib


'''optionalimport'''
def optionalimport(name: str, show_warning: bool = False):
    if name in sys.modules: return sys.modules[name]
    try:
        return importlib.import_module(name)
    except ModuleNotFoundError:
        missing = getattr(optionalimport, "_missing", set())
        if (name not in missing) and show_warning: warnings.warn(f'Optional dependency "{name}" is not installed; skipping import.', category=ImportWarning, stacklevel=2)
        missing.add(name)
        optionalimport._missing = missing
        return None


'''optionalimportfrom'''
def optionalimportfrom(module: str, attr: str, show_warning: bool = False):
    try:
        mod = sys.modules.get(module) or importlib.import_module(module)
        return getattr(mod, attr)
    except (ModuleNotFoundError, AttributeError):
        key = (module, attr)
        missing = getattr(optionalimportfrom, "_missing", set())
        if (key not in missing) and show_warning: warnings.warn(f"Optional import failed: from {module} import {attr}", ImportWarning, stacklevel=2)
        missing.add(key)
        optionalimportfrom._missing = missing
        return None