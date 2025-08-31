# sms_types.py
from __future__ import annotations

import abc
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Tuple

import ossm_base as base


@dataclass
class Metadata:
    name: str
    version: str
    date: str
    license: str
    author: List[str] = field(default_factory=list)
    keyword: List[str] = field(default_factory=list)
    description: Optional[str] = None

@dataclass
class Species:
    name: str
    ncbi_taxid: Optional[str] = None
    scope: Optional[str] = None

@dataclass
class Dim:
    name: Optional[str]
    size: Optional[int]  # -1 for wildcard, None unknown

@dataclass
class Shape:
    spec: Optional[str]
    dims: List[Dim] = field(default_factory=list)

@dataclass
class Port:
    id: str
    name: str
    dir: str
    dtype: str
    shape: Optional[Shape] = None
    module_id: Optional[str] = None

@dataclass
class Region:
    id: str
    name: Optional[str] = None
    atlas: Optional[str] = None

@dataclass
class Organ:
    id: str
    name: Optional[str] = None

@dataclass
class BodyPart:
    id: str
    name: Optional[str] = None

@dataclass
class ModuleCore(abc.ABC):
    id: str
    dt_ms: Optional[float] = None
    species: Optional[Species] = None
    ports: List[Port] = field(default_factory=list)

@dataclass
class Module(ModuleCore):
    region: Optional[Region] = None

@dataclass
class Sensor(ModuleCore):
    organ: Optional[Organ] = None

@dataclass
class Actuator(ModuleCore):
    body_part: Optional[BodyPart] = None

@dataclass
class Connection:
    from_id: str  # port id
    to_id: str    # port id
    delay_ms: Optional[float] = None

@dataclass(kw_only=True)
class Observable(base.types.Observable):
    id: str
    source_module: str
    source: str
    dt_ms: Optional[float] = None

@dataclass
class PortGroup:
    id: str
    members: List[str]  # list of port IDs
