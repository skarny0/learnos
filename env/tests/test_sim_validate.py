from learnos_env.sim.validate import all_checks


def test_sim_reproduces_known_effects():
    failed = [name for name, ok, _ in all_checks() if not ok]
    assert not failed, failed
