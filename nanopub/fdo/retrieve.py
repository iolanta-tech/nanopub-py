import requests
from nanopub import NanopubClient, Nanopub, NanopubConf
from nanopub.fdo.utils import looks_like_handle
from nanopub.fdo.fdo_record import FdoRecord
from nanopub.fdo import FdoNanopub
from rdflib import RDF, URIRef, Graph
from nanopub.namespaces import FDOF
from typing import Tuple, Optional

def resolve_id(iri_or_handle: str, conf: Optional[NanopubConf] = None) -> Tuple[FdoRecord, Optional[str]]:
    try:
        np = resolve_in_nanopub_network(iri_or_handle, conf=conf)
        if np is not None:
            record = FdoRecord(nanopub=np.assertion)
            return record, str(np.source_uri)

        if looks_like_handle(iri_or_handle):
            np = FdoNanopub.handle_to_nanopub(iri_or_handle)
            return FdoRecord(nanopub=np.assertion), str(np.source_uri)

        if iri_or_handle.startswith("https://hdl.handle.net/"):
            handle = iri_or_handle.replace("https://hdl.handle.net/", "")
            np = FdoNanopub.handle_to_nanopub(handle)
            return FdoRecord(nanopub=np.assertion), str(np.source_uri)

    except Exception as e:
        raise ValueError(f"Could not resolve FDO: {iri_or_handle}") from e

    raise ValueError(f"FDO not found: {iri_or_handle}")


def resolve_in_nanopub_network(iri_or_handle: str, conf: Optional[NanopubConf] = None) -> Optional[Nanopub]:
    query_id = "RAs0HI_KRAds4w_OOEMl-_ed0nZHFWdfePPXsDHf4kQkU"
    endpoint = "get-fdo-by-id"
    query_url = f"https://query.knowledgepixels.com/api/{query_id}/"
    np = None
    if conf is not None and conf.use_test_server:
        fetchConf = NanopubConf(
            use_test_server=True
        )
        np = Nanopub(iri_or_handle, conf=fetchConf)
    else:
        data = NanopubClient()._query_api_parsed(
            params={"fdoid": iri_or_handle},
            endpoint=endpoint,
            query_url=query_url,
        )
        np_uri = data[0].get("np")
        np = Nanopub(np_uri)
    if np is not None:
        return np
    return None
    
    

def retrieve_record_from_id(iri_or_handle: str):
    if looks_like_handle(iri_or_handle):
        np = FdoNanopub.handle_to_nanopub(iri_or_handle)
        return FdoRecord(nanopub=np.assertion)
    else:
        raise NotImplementedError("Non-handle IRIs not yet supported")


def retrieve_content_from_id(iri_or_handle: str) -> bytes:
    fdo_record, _ = resolve_id(iri_or_handle)

    content_url = fdo_record.get_data_ref()
    if not content_url:
        raise ValueError("FDO has no file / DataRef (isMaterializedBy)")

    response = requests.get(str(content_url))
    response.raise_for_status()
    return response.content


def resolve_handle_metadata(handle: str) -> dict:
    url = f"https://hdl.handle.net/api/handles/{handle}"
    response = requests.get(url)
    response.raise_for_status()
    return response.json()

def get_fdo_uri_from_fdo_record(assertion_graph: Graph) -> URIRef | None:
    for s, p, o in assertion_graph.triples((None, RDF.type, FDOF.FAIRDigitalObject)):
        if isinstance(s, URIRef):
            return s
    for s in assertion_graph.subjects():
        if isinstance(s, URIRef):
            return s
    return None