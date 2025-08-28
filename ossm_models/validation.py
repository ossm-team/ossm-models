# sms_validators.py
from __future__ import annotations
from typing import Iterable, List, Dict, Optional
import xmlschema
from ossm_models.core.types import Port, SensorBinding, ActuatorBinding

# ----- XSD validation -----

def validate_with_xsd(xml_path: str, xsd_path: str) -> xmlschema.XMLSchema:
    """
    Validate an instance XML against the schema. Raises on error.
    Returns the loaded schema object for optional reuse.
    """
    schema = xmlschema.XMLSchema(xsd_path)
    schema.validate(xml_path)  # raises XMLSchemaValidationError on failure
    return schema

# ----- light semantic checks (beyond XSD) -----

def axes(spec: Optional[str]) -> Optional[List[str]]:
    return None if not spec else [a.strip() for a in spec.split(",") if a.strip()]

def dims_map(port: Port) -> Dict[str, Optional[int]]:
    if not port.shape:
        return {}
    out: Dict[str, Optional[int]] = {}
    for d in port.shape.dims:
        if d.name:
            out[d.name] = d.size
    return out

def ports_compatible(src: Port, dst: Port) -> bool:
    # check dtype compatibility
    if src.dtype != dst.dtype:
        return False


    a_src = axes(src.shape.spec) if src.shape else None
    a_dst = axes(dst.shape.spec) if dst.shape else None
    if a_src is not None and a_dst is not None and a_src != a_dst:
        return False

    if not src.shape or not dst.shape:
        return True

    dm_s = dims_map(src)
    dm_d = dims_map(dst)
    for k in set(dm_s) | set(dm_d):
        vs, vd = dm_s.get(k), dm_d.get(k)
        if vs is None or vd is None:
            continue
        if vs != -1 and vd != -1 and vs != vd:
            return False
    return True

def check_sensor_actuator_xor(sensors: Iterable[SensorBinding],
                              actuators: Iterable[ActuatorBinding]) -> None:
    """
    Ensure each sensor has exactly one of maps_to/maps_to_group set (same for actuators).
    Raise ValueError on violation.
    """
    for s in sensors:
        both = bool(s.maps_to) and bool(s.maps_to_group)
        none = not s.maps_to and not s.maps_to_group
        if both or none:
            raise ValueError(f"sensor '{s.name}': set exactly one of maps_to or maps_to_group")
    for a in actuators:
        both = bool(a.maps_from) and bool(a.maps_from_group)
        none = not a.maps_from and not a.maps_from_group
        if both or none:
            raise ValueError(f"actuator '{a.name}': set exactly one of maps_from or maps_from_group")
