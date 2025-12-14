from ansible_collections.forwardnetworks.forward.plugins.filter.nqe import nqe_diff


def test_nqe_diff_basic():
    baseline = [{"name": "a"}, {"name": "b"}]
    current = [{"name": "b"}, {"name": "c"}]

    diff = nqe_diff(baseline, current)

    assert diff["removed"] == [{"name": "a"}]
    assert diff["added"] == [{"name": "c"}]
    assert diff["unchanged"] == [{"name": "b"}]
