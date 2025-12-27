"""Infrastructure resources - AFTER with graph-refs.

Import all resources with: from multi_file_after import *
"""

from .network import *
from .compute import *

__all__ = [
    # Network
    "Network",
    "Subnet",
    # Compute
    "SecurityGroup",
    "Instance",
]
