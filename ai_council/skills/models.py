"""Definitions for domain skills and their tool contracts."""
from dataclasses import dataclass, field
from enum import Enum


class Domain(str, Enum):
    ENGINEERING = 'engineering'
    FINANCE = 'finance'
    SECURITY = 'security'
    ARCHITECTURE = 'architecture'
    RESEARCH = 'research'
    GENERAL = 'general'


class BlastRadius(str, Enum):
    READ_ONLY = 'READ_ONLY'
    WORKSPACE_WRITE = 'WORKSPACE_WRITE'
    ISOLATED_SANDBOX = 'ISOLATED_SANDBOX'
    FULL_SYSTEM = 'FULL_SYSTEM'


@dataclass
class ToolContract:
    name: str
    domain: Domain
    blast_radius: BlastRadius
    timeout_s: float = 10.0
    read_only: bool = True


@dataclass
class SkillDefinition:
    name: str
    version: str
    domain: Domain
    description: str
    blast_radius: BlastRadius
    tools: list[ToolContract] = field(default_factory=list)
    negative_constraints: list[str] = field(default_factory=list)
