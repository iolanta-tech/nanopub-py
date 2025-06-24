from rdflib import URIRef
from nanopub.namespaces import FDOF
from nanopub.fdo.fdo_nanopub import FdoNanopub
from nanopub.fdo.fdo_record import FdoRecord
from nanopub.fdo.retrieve import get_fdo_uri_from_fdo_record

def update_record(fdo_nanopub: FdoNanopub, record: FdoRecord) -> URIRef:
    """
    Update the assertion graph of the given FdoNanopub using triples from the provided FdoRecord.
    Then update the nanopub.

    Returns the source URI of the updated nanopub.
    """
    assertion_graph = fdo_nanopub.assertion
    subject_uri = get_fdo_uri_from_fdo_record(assertion_graph)
    if subject_uri is None:
        raise ValueError("Could not find subject URI in the FdoNanopub assertion graph.")

    for p, o in list(assertion_graph.predicate_objects(subject=subject_uri)):
        assertion_graph.remove((subject_uri, p, o))

    for triple in record.get_statements():
        assertion_graph.add(triple)

    fdo_nanopub.update()

    return fdo_nanopub.source_uri