from typing import Dict
from typing import List
from typing import Optional
from xml.etree import ElementTree as ET

from ossm_models.core.configs import NS

from ossm_models.core.types import (
    ActuatorBinding, Connection, Contract, Dim, Metadata, Module,
    Observable, Port, PortGroup, SensorBinding, Shape, Species
)


def _parse_contract(e: Optional[ET.Element]) -> Optional[Contract]:
    if e is None:
        return None
    rate = e.get("dt_ms")

    sensors: List[SensorBinding] = []
    for s in e.findall("sms:sensor", NS):
        sensors.append(SensorBinding(
            name=s.get("name"),
            modality=s.get("modality"),
            maps_to=s.get("maps_to"),
            maps_to_group=s.get("maps_to_group"),
        ))

    actuators: List[ActuatorBinding] = []
    for a in e.findall("sms:actuator", NS):
        actuators.append(ActuatorBinding(
            name=a.get("name"),
            effector=a.get("effector"),
            maps_from=a.get("maps_from"),
            maps_from_group=a.get("maps_from_group"),
        ))
    return Contract(
        dt_ms=None if rate is None else float(rate),
        sensors=sensors,
        actuators=actuators,
    )


def _parse_port_groups(root: ET.Element) -> Dict[str, PortGroup]:
    out: Dict[str, PortGroup] = {}
    pg = root.find("sms:port_groups", NS)
    if pg is None:
        return out
    for g in pg.findall("sms:port_group", NS):
        gid = g.get("id")
        members = [m.get("ref") for m in g.findall("sms:member", NS)]
        out[gid] = PortGroup(id=gid, members=members)
    return out


def _parse_observable(e: ET.Element) -> Observable:
    rate = e.get("dt_ms")
    return Observable(
        id=e.get("id"),
        source_module=e.get("source_module"),
        source=e.get("source"),
        dt_ms=None if rate is None else float(rate),
    )


def _parse_connection(e: ET.Element) -> Connection:
    delay = e.get("delay_ms")

    return Connection(
        from_id=e.get("from"),
        to_id=e.get("to"),
        delay_ms=None if delay is None else float(delay),
    )


def _parse_module(e: ET.Element) -> Module:
    io = e.find("sms:io", NS)
    module_id = e.get("id")
    ports: List[Port] = []
    if io is not None:
        ports = [_parse_port(p, module_id) for p in io.findall("sms:port", NS)]
    dt = e.get("dt_ms")
    return Module(
        id=module_id,
        dt_ms=None if dt is None else float(dt),
        region=e.get("region"),
        species=_parse_species(e.find("sms:species", NS)),
        ports=ports,
    )


def _parse_port(e: ET.Element, module_id) -> Port:
    rate = e.get("rate_hz")
    return Port(
        id=e.get("id"),
        name=e.get("name"),
        dir=e.get("dir"),
        dtype=e.get("dtype"),
        shape=_parse_shape(e.find("sms:shape", NS)),
        module_id=module_id,
    )


def _parse_shape(e: Optional[ET.Element]) -> Optional[Shape]:
    if e is None:
        return None
    dims: List[Dim] = []
    for d in e.findall("sms:dim", NS):
        size = d.get("size")
        dims.append(Dim(name=d.get("name"), size=None if size is None else int(size)))
    return Shape(spec=e.get("spec"), dims=dims)


def _parse_species(e: Optional[ET.Element]) -> Optional[Species]:
    if e is None:
        return None
    return Species(e.get("name"), e.get("ncbi_taxid"), e.get("scope"))


def _parse_metadata(e: ET.Element) -> Metadata:
    def texts(tag: str) -> List[str]:
        return [x.text for x in e.findall(f"sms:{tag}", NS) if x.text]
    return Metadata(
        name=e.findtext("sms:name", default="", namespaces=NS),
        version=e.findtext("sms:version", default="", namespaces=NS),
        date=e.findtext("sms:date", default="", namespaces=NS),
        license=e.findtext("sms:license", default="", namespaces=NS),
        author=texts("author"),
        keyword=texts("keyword"),
        description=e.findtext("sms:description", default=None, namespaces=NS),
    )
