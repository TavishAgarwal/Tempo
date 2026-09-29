from taqpso.config import load_config


def test_default_config_loads_and_hashes() -> None:
    cfg = load_config()
    assert cfg.stall.iterations == 30
    assert cfg.weights().w_T == 1.0
    assert cfg.hash() == load_config().hash()


def test_override_merge() -> None:
    cfg = load_config({"swarm": {"size": 5}})
    assert cfg.swarm.size == 5 and cfg.swarm.alpha_end == 0.5
