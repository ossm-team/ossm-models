""" Model class following the OSSM standards v0.4."""
import abc
from typing import Dict, List, Tuple, Optional

import xml.etree.ElementTree as ET
import networkx as nx
import numpy as np

from ossm_models.core.configs import NS

from ossm_models.core.parsers import (
    _parse_contract, _parse_metadata, _parse_module,
    _parse_observable, _parse_port_groups, _parse_species,
    _parse_connection
)

from ossm_models.core.types import (
    Metadata, Species, Port, Module, Connection, Observable,
    PortGroup, SensorBinding, ActuatorBinding, Contract
)
from ossm_models.validation import validate_with_xsd, ports_compatible, check_sensor_actuator_xor


class SMSModel:
    
    def __init__(
        self,
        metadata: Metadata,
        species: Optional[Species],
        time_base_dt_ms: Optional[float],
        modules: List[Module],
        connections: List[Connection],
        observables: List[Observable],
        port_groups: Dict[str, PortGroup],
        contract: Optional[Contract],
    ):
        self.metadata = metadata
        self.species = species
        self.time_base_dt_ms = time_base_dt_ms
        self.modules = modules
        self.connections = connections
        self.observables = observables
        self.port_groups = port_groups
        self.contract = contract

        # indices
        self.module_by_id: Dict[str, Module] = {m.id: m for m in self.modules}
        self.port_by_id: Dict[str, Port] = {}

        for m in self.modules:
            for p in m.ports:
                if p.id in self.port_by_id:
                    raise ValueError(f"duplicate port id: {p.id}")
                self.port_by_id[p.id] = p

    @property
    def n_modules(self) -> int:
        return len(self.modules)

    @classmethod
    def from_xml(cls, xml_path: str) -> "SMSModel":
        validate_with_xsd(xml_path, "../SMS.xsd")

        root = ET.parse(xml_path).getroot()
        md = _parse_metadata(root.find("sms:metadata", NS))
        species = _parse_species(root.find("sms:species", NS))
        tb = root.find("sms:time_base", NS)
        time_base_dt_ms = float(tb.get("dt_ms")) if (tb is not None and tb.get("dt_ms")) else None

        modules = [_parse_module(e) for e in root.findall("sms:modules/sms:module", NS)]
        connections = []
        conns_node = root.find("sms:connections", NS)
        if conns_node is not None:
            connections = [_parse_connection(c) for c in conns_node.findall("sms:connection", NS)]
        observables = []
        obs_node = root.find("sms:observables", NS)
        if obs_node is not None:
            observables = [_parse_observable(o) for o in obs_node.findall("sms:observable", NS)]
        port_groups = _parse_port_groups(root)
        contract = _parse_contract(root.find("sms:contract", NS))

        model = cls(md, species, time_base_dt_ms, modules, connections, observables, port_groups, contract)
        # optional semantic checks
        if model.contract:
            check_sensor_actuator_xor(model.contract.sensors, model.contract.actuators)
        return model

    def resolve_connection_ports(self, c: Connection) -> Tuple[Port, Port]:
        """ Return (from_port, to_port) for a connection. """
        return self.port_by_id[c.from_id], self.port_by_id[c.to_id]

    def sensor_targets(self, s: SensorBinding) -> List[Port]:
        if s.maps_to and s.maps_to_group:
            raise ValueError(f"sensor {s.name}: both maps_to and maps_to_group set")
        if s.maps_to:
            return [self.port_by_id[s.maps_to]]
        if s.maps_to_group:
            group = self.port_groups.get(s.maps_to_group)
            if not group:
                raise KeyError(f"unknown port_group: {s.maps_to_group}")
            return [self.port_by_id[pid] for pid in group.members]
        return []

    def actuator_sources(self, a: ActuatorBinding) -> List[Port]:
        if a.maps_from and a.maps_from_group:
            raise ValueError(f"actuator {a.name}: both maps_from and maps_from_group set")
        if a.maps_from:
            return [self.port_by_id[a.maps_from]]
        if a.maps_from_group:
            group = self.port_groups.get(a.maps_from_group)
            if not group:
                raise KeyError(f"unknown port_group: {a.maps_from_group}")
            return [self.port_by_id[pid] for pid in group.members]
        return []

    def build_graphs(self) -> tuple[nx.MultiDiGraph, nx.DiGraph]:
        """
        Return (port_graph, module_graph)
        - port_graph nodes: ports (by id) + optional 'sensor:*' / 'actuator:*' nodes
        - port_graph edges: connection, sensor_binding, actuator_binding
        - module_graph nodes: modules
        - module_graph edges: aggregated by module with 'port_pairs' list
        """
        port_g = nx.MultiDiGraph(name="sms_port_graph")
        mod_g = nx.DiGraph(name="sms_module_graph")

        for m in self.modules:
            mod_g.add_node(m.id, dt_ms=m.dt_ms, region=m.region)

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

        if self.contract:
            for s in self.contract.sensors:
                targets = self.sensor_targets(s)
                if targets:
                    s_node = f"sensor:{s.name}"
                    port_g.add_node(s_node, kind="sensor", modality=s.modality)
                    for p in targets:
                        port_g.add_edge(s_node, p.id, kind="sensor_binding")

            for a in self.contract.actuators:
                sources = self.actuator_sources(a)
                if sources:
                    a_node = f"actuator:{a.name}"
                    port_g.add_node(a_node, kind="actuator", effector=a.effector)
                    for p in sources:
                        port_g.add_edge(p.id, a_node, kind="actuator_binding")

        return port_g, mod_g

    def check_connections_compatibility(self) -> List[Tuple[str, str]]:
        """
        Return a list of (src_port_id, dst_port_id) pairs that are incompatible
        (dtype/modality/shape). Empty list ⇒ all good.
        """
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


class OSSMModel(SMSModel, abc.ABC):
    """ Interface for sensorimotor models. Implements the OSSM modeling standards.

    The interface standardizes the initialization and operation of models within the standards. The implementation
    itself is left to the specific model.

    Multiple extensions of the interface will exist for different autodifferentiation frameworks,
    e.g. PyTorch or TensorFlow.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    @abc.abstractmethod
    def initialize(self) -> "OSSMModel":
        """ Initialize the model before starting a simulation. Returns itself. """
        pass

    @abc.abstractmethod
    def simulate(self) -> "OSSMModel":
        """ Run a single timestep of the model simulation. Returns itself. """
        pass

    @abc.abstractmethod
    def record(self) -> Dict[Observable, np.ndarray]:
        """ Measure the observables of the model. """
        pass


class _TestOSSMModel(OSSMModel):
    """ A simple test implementation of the OSSMModel interface. """

    def initialize(self):
        print("initialize model")

    def simulate(self):
        print("simulate model")

    def record(self):
        print("record observables")


if __name__ == "__main__":
    model = _TestOSSMModel.from_xml("../model-sample/sample_fpn.xml", )
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
