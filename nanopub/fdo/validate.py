import json
import requests
from pyshacl import validate
from rdflib import Graph
from nanopub.fdo.utils import convert_jsonschema_to_shacl, looks_like_handle
from nanopub.fdo.retrieve import resolve_in_nanopub_network
from nanopub.fdo.fdo_record import FdoRecord 
from nanopub.fdo.fdo_nanopub import FdoNanopub
from nanopub.namespaces import FDOC
from rdflib.namespace import SH
from typing import List
from dataclasses import dataclass

@dataclass
class ValidationResult:
    is_valid: bool
    errors: List[str]
    warnings: List[str]

def validate_fdo_record(record: FdoRecord) -> ValidationResult:
    try:
        profile_uri = record.get_profile()
        if not profile_uri:
            return ValidationResult(False, ["FDO profile URI not found in record."], [])

        if looks_like_handle(profile_uri):
            profile_uri = FdoNanopub.handle_to_nanopub(profile_uri).fdo_profile
            handle = str(profile_uri).split("/")[-1]
            profile_api_url = f"https://hdl.handle.net/api/handles/{handle}"
            profile_response = requests.get(profile_api_url)
            profile_data = profile_response.json()

            jsonschema_entry = next(
                (v for v in profile_data.get("values", []) if v.get("type") == "21.T11966/JsonSchema"),
                None
            )

            if not jsonschema_entry:
                return ValidationResult(False, ["JSON Schema entry not found in FDO profile."], [])

            raw_value = jsonschema_entry["data"]["value"]
            parsed_value = json.loads(raw_value)
            jsonschema_url = parsed_value.get("$ref")

            if not jsonschema_url:
                return ValidationResult(False, ["JSON Schema $ref not found."], [])

            schema_response = requests.get(jsonschema_url)
            json_schema = schema_response.json()
            shape_graph = convert_jsonschema_to_shacl(json_schema)

        else:
            shape_graph = Graph()
            profile = resolve_in_nanopub_network(profile_uri)
            if not profile:
                profile_response = requests.get(profile_uri, headers={"Accept": "application/ld+json"})
                if profile_response.status_code != 200:
                    return ValidationResult(False, [f"Failed to fetch profile: {profile_response.status_code}"], [])

                profile_data = profile_response.json()
                shape_uri = None
                profile_uri_str = str(profile_uri)

                for item in profile_data:
                    for node in item.get('@graph', []):
                        if node.get('@id') == profile_uri_str:
                            has_shape = node.get(str(FDOC.hasShape))
                            if has_shape and isinstance(has_shape, list):
                                shape_uri = has_shape[0].get('@id')
                            break
                    if shape_uri:
                        break

                if not shape_uri:
                    return ValidationResult(False, ["No hasShape found in profile JSON-LD"], [])

                shape_graph.parse(shape_uri, format='json-ld')

        graph = record.get_graph()

        conforms, results_graph, results_text = validate(
            graph,
            shacl_graph=shape_graph,
            inference='rdfs',
            abort_on_first=False,
            meta_shacl=False,
            advanced=True,
            debug=False
        )

        errors = []
        warnings = []

        if not conforms:
            # Extracting messages from SHACL results graph
            for s, p, o in results_graph.triples((None, SH.resultMessage, None)):
                errors.append(str(o))

        return ValidationResult(conforms, errors, warnings)

    except Exception as e:
        return ValidationResult(False, [f"Validation error: {str(e)}"], [])
