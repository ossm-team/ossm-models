# sms_types.py
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Tuple

# ----- core datatypes (purely declarative) -----

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
class Module:
    id: str
    dt_ms: Optional[float] = None
    region: Optional[str] = None
    species: Optional[Species] = None
    ports: List[Port] = field(default_factory=list)

@dataclass
class Connection:
    from_id: str  # port id
    to_id: str    # port id
    delay_ms: Optional[float] = None

@dataclass
class Observable:
    id: str
    source_module: str
    source: str
    dt_ms: Optional[float] = None

@dataclass
class PortGroup:
    id: str
    members: List[str]  # list of port IDs

@dataclass
class SensorBinding:
    name: str
    modality: str
    maps_to: Optional[str] = None         # port id
    maps_to_group: Optional[str] = None   # group id

@dataclass
class ActuatorBinding:
    name: str
    effector: Optional[str] = None
    maps_from: Optional[str] = None
    maps_from_group: Optional[str] = None

@dataclass
class Contract:
    dt_ms: Optional[float] = None
    sensors: List[SensorBinding] = field(default_factory=list)
    actuators: List[ActuatorBinding] = field(default_factory=list)
