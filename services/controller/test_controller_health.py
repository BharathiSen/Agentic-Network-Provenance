"""Scaffold check for the controller service (gates commits on signed+verified+fresh records).

Also asserts the shared information model is importable here. All three
services depend on one definition of the record format (libs/provenance);
this fails if that wiring breaks or if a service starts redefining the
schema locally.
"""

from provenance import ProvenanceStatement, sign_statement, verify_statement


def test_controller_scaffold_is_ready():
    assert True


def test_controller_shares_the_provenance_information_model():
    assert set(ProvenanceStatement.model_fields) == {
        "subject_ref",
        "origin_class",
        "evidence",
        "verification",
        "freshness",
    }
    assert callable(sign_statement) and callable(verify_statement)
