"""Test package for the evaluation modules.

This directory is itself an importable package named ``evaluation``, so pytest
imports test modules as ``evaluation.test_metrics`` and the name shadows the
source package at ``plugin/evaluation``.  Source modules are therefore loaded
by file path under distinct module names.
"""
from __future__ import annotations

import importlib.util
import os
import sys
from types import ModuleType

PLUGIN_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SOURCE_DIR = os.path.join(PLUGIN_ROOT, "evaluation")
# Product submodules such as evaluation.run import evaluation.cache normally.
# Point this test package's search path at the real source package too, so those
# imports resolve while test-only module names stay distinct.
__path__ = [os.path.dirname(os.path.abspath(__file__)), SOURCE_DIR]


def load(name: str) -> ModuleType:
    """Import ``plugin/evaluation/<name>.py`` without relying on package names."""
    module_name = f"antemuse_evaluation_{name}"
    if module_name in sys.modules:
        return sys.modules[module_name]
    path = os.path.join(SOURCE_DIR, f"{name}.py")
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load {name} from {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module
