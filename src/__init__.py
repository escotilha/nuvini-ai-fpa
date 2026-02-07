"""
Nuvini AI FP&A - Monthly Close Automation System

Multi-agent system for automating financial planning & analysis monthly close
for 7 portfolio companies with IFRS/US GAAP compliance.
"""

__version__ = "0.1.0"
__author__ = "Nuvini Group Limited"
__license__ = "Proprietary"

from . import core, connectors, consolidation, analysis, reporting, orchestration

__all__ = [
    "core",
    "connectors",
    "consolidation",
    "analysis",
    "reporting",
    "orchestration",
]
