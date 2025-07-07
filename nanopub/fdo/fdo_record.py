from rdflib import Graph, URIRef, Literal
from typing import Optional, Union
from rdflib.namespace import RDFS, DCTERMS
from nanopub.namespaces import HDL, FDOF, FDOC


class FdoRecord:
    """
    EXPERIMENTAL: This class is experimental and may change or be removed in future versions.

    Can be initialized from an assertion graph OR from explicit params.
    """

    def __init__(
        self,
        nanopub: Optional[Graph] = None,
        *,
        profile_uri: Optional[Union[str, URIRef]] = None,
        label: Optional[str] = None,
        dataref: Optional[Union[str, URIRef]] = None,
    ):
        self.id: Optional[str] = None
        self.tuples: dict[URIRef, Union[Literal, URIRef]] = {}

        if nanopub:
            # Init from assertion graph
            for s, p, o in nanopub:
                # Accept both DCTERMS.conformsTo and FDOC.hasFdoProfile
                if (p == DCTERMS.conformsTo or p == FDOC.hasFdoProfile) and self.id is None:
                    self.id = self.extract_handle(o)
                self.tuples[p] = o

            if self.id is None:
                raise ValueError("Missing required FDO profile statement")

        if nanopub is None:
            # Init from explicit params
            if profile_uri is None:
                raise ValueError("profile_uri is required when nanopub assertion graph not given")

            self.set_profile(profile_uri)
            if label:
                self.set_label(label)
            if dataref:
                self.set_data_ref(dataref)

            # Extract handle from profile_uri if possible
            self.id = self.extract_handle(profile_uri) if self.id is None else self.id

    def __str__(self) -> str:
        label = self.get_label() or "No label"
        profile = self.get_profile() or "No profile"
        return f"FDO Record\n  ID: {self.id}\n  Label: {label}\n  Profile: {profile}"

    def __repr__(self) -> str:
        return self.__str__()

    def extract_handle(self, subject: Union[str, URIRef]) -> str:
        # Handle both URIRef and str
        s = str(subject)
        return s.split("/")[-1]

    def get_statements(self) -> list[tuple[URIRef, URIRef, Union[Literal, URIRef]]]:
        if not self.id:
            raise ValueError("FDO ID is not set")
        subject = URIRef(f"https://hdl.handle.net/{self.id}")
        return [(subject, p, o) for p, o in self.tuples.items()]

    def get_graph(self) -> Graph:
        g = Graph()
        for s, p, o in self.get_statements():
            g.add((s, p, o))
        return g

    def get_profile(self) -> Optional[URIRef]:
        val = self.tuples.get(DCTERMS.conformsTo) or self.tuples.get(FDOC.hasFdoProfile)
        return URIRef(val) if val else None

    def get_data_ref(self) -> Optional[URIRef]:
        val = self.tuples.get(FDOF.isMaterializedBy)
        return URIRef(val) if val else None

    def get_label(self) -> Optional[str]:
        val = self.tuples.get(RDFS.label)
        return str(val) if val else None

    def get_id(self) -> Optional[str]:
        return self.id

    def set_id(self, handle: str) -> None:
        self.id = handle

    def set_label(self, label: str) -> None:
        self.tuples[RDFS.label] = Literal(label)

    def set_profile(self, uri: Union[str, URIRef], use_fdof: bool = False) -> None:
        pred = FDOC.hasFdoProfile if use_fdof else DCTERMS.conformsTo
        self.tuples[pred] = URIRef(uri)

    def set_data_ref(self, uri: Union[str, URIRef]) -> None:
        self.tuples[FDOF.isMaterializedBy] = URIRef(uri)

    def set_property(self, predicate: Union[str, URIRef], value: Union[str, URIRef, Literal]) -> None:
        pred = URIRef(predicate)
        obj = URIRef(value) if isinstance(value, str) and value.startswith("http") else Literal(value)
        self.tuples[pred] = obj
        
    def add_aggregate(self, iri: URIRef):
        existing = self.tuples.get(DCTERMS.hasPart)
        if existing:
            if isinstance(existing, list):
                existing.append(iri)
            else:
                self.tuples[DCTERMS.hasPart] = [existing, iri]
        else:
            self.tuples[DCTERMS.hasPart] = iri

    def copy(self) -> "FdoRecord":
        new_record = FdoRecord()
        new_record.id = self.id
        new_record.tuples = self.tuples.copy()
        return new_record
