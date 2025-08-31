""" Model class following the OSSM standards v0.4."""
import os.path
import xml.etree.ElementTree as ET
from typing import Dict
from typing import List
from typing import Optional
from typing import Tuple

import networkx as nx
import ossm_base as base
from ossm_base.model import OSSMModel

from ossm_models.core.configs import NS
from ossm_models.core.parsers import _parse_connection
from ossm_models.core.parsers import _parse_metadata
from ossm_models.core.parsers import _parse_module
from ossm_models.core.parsers import _parse_observable
from ossm_models.core.parsers import _parse_port_groups
from ossm_models.core.parsers import _parse_species
from ossm_models.core.sms_types import Actuator
from ossm_models.core.sms_types import Connection
from ossm_models.core.sms_types import Metadata
from ossm_models.core.sms_types import Module
from ossm_models.core.sms_types import ModuleCore
from ossm_models.core.sms_types import Observable
from ossm_models.core.sms_types import Port
from ossm_models.core.sms_types import PortGroup
from ossm_models.core.sms_types import Sensor
from ossm_models.core.sms_types import Species
from ossm_models.validation import ports_compatible
from ossm_models.validation import validate_with_xsd


class SMSModel(OSSMModel):
    
    def __init__(
        self,
        metadata: Metadata,
        species: Optional[Species],
        time_base_dt_ms: Optional[float],
        modules: List[Module],
        sensors: List[Sensor],
        actuators: List[Actuator],
        connections: List[Connection],
        observables: List[Observable],
        port_groups: Dict[str, PortGroup],
    ):
        self.metadata = metadata
        self.species = species
        self.time_base_dt_ms = time_base_dt_ms
        self.modules = modules
        self.sensors = sensors
        self.actuators = actuators
        self.connections = connections
        self.observables = observables
        self.port_groups = port_groups

        # indices
        self.module_by_id: Dict[str, ModuleCore] = {m.id: m for m in self.module_types}
        self.port_by_id: Dict[str, Port] = {}

        for m in self.module_types:
            for p in m.ports:
                if p.id in self.port_by_id:
                    raise ValueError(f"duplicate port id: {p.id}")
                self.port_by_id[p.id] = p

    @property
    def n_modules(self) -> int:
        return len(self.modules)

    @property
    def module_types(self) -> List[ModuleCore]:
        return self.modules + self.sensors + self.actuators

    @classmethod
    def from_xml(cls, xml_path: str) -> "SMSModel":
        validate_with_xsd(
            xml_path,
            os.path.join(
                os.path.dirname(os.path.realpath(__file__)),
                "../../SMS.xsd"
            )
        )

        root = ET.parse(xml_path).getroot()
        md = _parse_metadata(root.find("sms:metadata", NS))
        species = _parse_species(root.find("sms:species", NS))
        tb = root.find("sms:time_base", NS)
        time_base_dt_ms = float(tb.get("dt_ms")) if (tb is not None and tb.get("dt_ms")) else None

        modules = [_parse_module(e) for e in root.findall("sms:modules/sms:module", NS)]
        sensors = [_parse_module(e) for e in root.findall("sms:modules/sms:sensor", NS)]
        actuators = [_parse_module(e) for e in root.findall("sms:modules/sms:actuator", NS)]

        connections = []
        conns_node = root.find("sms:connections", NS)
        if conns_node is not None:
            connections = [_parse_connection(c) for c in conns_node.findall("sms:connection", NS)]
        observables = []
        obs_node = root.find("sms:observables", NS)
        if obs_node is not None:
            observables = [_parse_observable(o) for o in obs_node.findall("sms:observable", NS)]
        port_groups = _parse_port_groups(root)

        model = cls(md, species, time_base_dt_ms, modules, sensors, actuators, connections, observables, port_groups)

        return model

    def resolve_connection_ports(self, c: Connection) -> Tuple[Port, Port]:
        """ Return (from_port, to_port) for a connection. """
        return self.port_by_id[c.from_id], self.port_by_id[c.to_id]

    def build_graphs(self) -> tuple[nx.MultiDiGraph, nx.DiGraph]:
        """ Build and return the port graph and module graph. """

        port_g = nx.MultiDiGraph(name="sms_port_graph")
        mod_g = nx.DiGraph(name="sms_module_graph")

        for m in self.module_types:
            if isinstance(m, Sensor):
                mod_g.add_node(m.id, dt_ms=m.dt_ms, organ=m.organ.id if m.organ else None)
            elif isinstance(m, Actuator):
                mod_g.add_node(m.id, dt_ms=m.dt_ms, body_part=m.body_part.id if m.body_part else None)
            elif isinstance(m, Module):
                mod_g.add_node(m.id, dt_ms=m.dt_ms, region=m.region if m.region else None)
            else:
                raise NotImplementedError(m.id)

            for p in m.ports:
                # flatten shape for attributes
                shape_spec = p.shape.spec if p.shape else None
                dims = [(d.name, d.size) for d in (p.shape.dims if p.shape else [])]
                port_g.add_node(
                    p.id,
                    module=m.id, name=p.name, dir=p.dir, dtype=p.dtype,
                    shape_spec=shape_spec, shape_dims=dims
                )

            # add implicit internal connections from input to output ports
            in_ports = [p for p in m.ports if p.dir == "in"]
            out_ports = [p for p in m.ports if p.dir == "out"]

            for ip in in_ports:
                for op in out_ports:
                    port_g.add_edge(ip.id, op.id, kind="internal")

        for c in self.connections:
            sp, dp = self.resolve_connection_ports(c)
            port_g.add_edge(sp.id, dp.id, kind="connection",
                            delay_ms=c.delay_ms,
                            from_id=c.from_id, to_id=c.to_id)

            # add/aggregate module edges
            if not mod_g.has_edge(sp.module_id, dp.module_id):
                mod_g.add_edge(sp.module_id, dp.module_id, kind="connection")

            # aggregate port pairs on module edges
            me = mod_g.edges[sp.module_id, dp.module_id]
            if "port_pairs" not in me:
                me["port_pairs"] = []

            me["port_pairs"].append((sp.id, dp.id))

        return port_g, mod_g

    def check_connections_compatibility(self) -> List[Tuple[str, str]]:
        """ Check all connections for port compatibility. """

        mismatches: List[Tuple[str, str]] = []
        for c in self.connections:
            sp, dp = self.resolve_connection_ports(c)
            if not ports_compatible(sp, dp):
                mismatches.append((sp.id, dp.id))
        return mismatches

    # VISUALIZATION

    def viz_model_graph(self):
        """ Visualize the port graph using matplotlib. """
        try:
            import matplotlib.pyplot as plt
        except ImportError:
            raise ImportError("matplotlib is required for visualization")

        port_g, mod_g = self.build_graphs()

        plt.figure(figsize=(12, 10))

        pos = nx.spring_layout(port_g, seed=42)

        node_colors = []
        for n, d in port_g.nodes(data=True):
            if d.get('kind') == 'sensor':
                node_colors.append('lightgreen')
            elif d.get('kind') == 'actuator':
                node_colors.append('lightblue')
            else:
                node_colors.append('lightgray')

        edge_colors = []
        for u, v, d in port_g.edges(data=True):
            if d.get('kind') == 'connection':
                edge_colors.append('blue')
            elif d.get('kind') == 'internal':
                edge_colors.append('lightgray')
            elif d.get('kind') == 'sensor':
                edge_colors.append('green')
            elif d.get('kind') == 'actuator':
                edge_colors.append('orange')
            else:
                edge_colors.append('gray')

        nx.draw_networkx_nodes(port_g, pos, nodelist=port_g.nodes(), node_color=node_colors, node_size=2500)
        nx.draw_networkx_edges(port_g, pos, edgelist=port_g.edges(), edge_color=edge_colors, arrows=True)
        nx.draw_networkx_labels(port_g, pos, font_size=8)

        plt.show()


class TestOSSMModel(SMSModel):
    """ A simple test implementation of the OSSMModel interface. """

    def initialize(self):
        print("initialize model")

    def simulate(self, stimulus):
        print("simulate model")

    def record(self):
        print("record observables")


if __name__ == "__main__":
    model = TestOSSMModel.from_xml("../../examples/sample_fpn.xml", )
    port_g, mod_g = model.build_graphs()

    print(f"modules: {mod_g.number_of_nodes()} edges: {mod_g.number_of_edges()}")
    print(f"ports:   {port_g.number_of_nodes()} connections: "
          f"{sum(1 for _,_,d in port_g.edges(data=True) if d.get('kind')=='connection')}")

    # visualize port graph
    model.viz_model_graph()

    mismatches = model.check_connections_compatibility()
    if mismatches:
        print("incompatible connections:")
        for u, v in mismatches:
            pu, pv = port_g.nodes[u], port_g.nodes[v]
            print(f" - {pu['module']}.{pu['name']} -> {pv['module']}.{pv['name']}")
    else:
        print("all connections compatible")
