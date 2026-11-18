from finaira.v2.sentence_benchmark import generate_sentence_requests, verified_value_pools


def test_sentence_benchmark_pools_are_exact_direct_and_policy_backed():
    pools = verified_value_pools(max_values_per_type=2)
    for entity_type in ("BANK", "COUNTRY", "NATIONALITY", "JOB_TITLE"):
        assert pools[entity_type]
        assert all(item["resolution_status"] in {"MATCHED", "VERIFIED"} for item in pools[entity_type])
        assert all(item["exact_candidate_id"] for item in pools[entity_type])


def test_sentence_generator_creates_many_annotated_offsets():
    requests, manifest = generate_sentence_requests(count=12, seed=7)
    assert len(requests) == 12
    assert manifest["languages"] == {"en": 6, "ar": 6}
    for request in requests:
        assert request["entities"]
        for entity in request["entities"]:
            assert request["document"][entity["start"]:entity["end"]] == entity["original"]
            assert entity["type"] in {"AGE", "JOB_TITLE", "BANK", "NATIONALITY", "COUNTRY"}
