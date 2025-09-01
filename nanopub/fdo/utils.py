import rdflib
from rdflib import RDF, URIRef, Literal, Namespace, Graph
from rdflib.namespace import SH, XSD

EX = Namespace("https://example.org/shapes")
HDL = Namespace("https://hdl.handle.net/")

NUMERIC_SHACL_PROPS = [
    SH.maxCount,
    SH.minCount,
    SH.minExclusive,
    SH.maxExclusive,
    SH.minInclusive,
    SH.maxInclusive
]

def fix_numeric_shacl_constraints(shape_graph: Graph) -> Graph:
    """
    Convert string literals used as SHACL numeric constraints into xsd:integer literals.
    """
    for prop in NUMERIC_SHACL_PROPS:
        for s, p, o in list(shape_graph.triples((None, prop, None))):
            if not (o.datatype == XSD.integer):
                try:
                    value = int(str(o))
                    shape_graph.set((s, p, Literal(value, datatype=XSD.integer)))
                except ValueError:
                    pass

    return shape_graph


def looks_like_handle(value: str) -> bool:
    return isinstance(value, str) and not value.startswith("http")

def looks_like_url(s: str) -> bool:
    return s.startswith("http://") or s.startswith("https://")

def handle_to_iri(handle: str) -> rdflib.URIRef:
    return rdflib.URIRef(f"https://hdl.handle.net/{handle}")


def convert_jsonschema_to_shacl(json_schema: dict) -> rdflib.Graph:
    g = rdflib.Graph()
    g.bind("sh", SH)
    g.bind("xsd", XSD)
    g.bind("ex", EX)
    g.bind("hdl", HDL)

    node_shape = EX["FdoProfileShape"]
    g.add((node_shape, RDF.type, SH.NodeShape))
    g.add((node_shape, SH.targetClass, URIRef("https://w3id.org/fdof/ontology#FairDigitalObject")))
    g.add((node_shape, SH.closed, Literal(False)))

    for field in json_schema.get("required", []):
        prop_shape = EX[field.replace("/", "_")]
        g.add((node_shape, SH.property, prop_shape))
        g.add((prop_shape, RDF.type, SH.PropertyShape))
        g.add((prop_shape, SH.path, URIRef(f"https://hdl.handle.net/{field}")))
        g.add((prop_shape, SH.minCount, Literal(1)))
        g.add((prop_shape, SH.maxCount, Literal(1)))
        g.add((prop_shape, SH.datatype, XSD.string))

    return g
