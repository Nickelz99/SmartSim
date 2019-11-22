from smartsim import Generator, State
from os import path, environ
from shutil import rmtree
from ..error import SmartSimError, SSModelExistsError
import pytest


def test_generator_python_interface():
    """Test for the creation of the experiment directory structure when both create_target
    and create_model are used (programmatic interface)."""

    experiment_dir = "./lammps_atm"
    if path.isdir(experiment_dir):
        rmtree(experiment_dir)

    state = State(experiment="lammps_atm")

    param_dict = {"25": [20, 25]}
    state.create_target("atm", params=param_dict)
    state.create_model("add_1", "atm", {"25": 90})

    # Supply the generator with necessary files to run the simulation
    # and generate the specified models
    base_config = "../../examples/LAMMPS/in.atm"
    gen = Generator(state, model_files=base_config)
    gen.generate()

    # assert that experiment directory was created
    assert(path.isdir(experiment_dir))
    target = path.join(experiment_dir, "atm")
    assert(path.isdir(target))

    target_model_1 = path.join(target, "atm_0")
    target_model_2 = path.join(target, "atm_1")
    target_model_3 = path.join(target, "add_1")

    model_dirs = [target_model_1, target_model_2,
                  target_model_3]
    # check for model dir and listed configuration file
    for model in model_dirs:
        assert(path.isdir(model))
        assert(path.isfile(path.join(model, "in.atm")))

    if path.isdir(experiment_dir):
        rmtree(experiment_dir)

def test_gen_with_user_created_models():
    """Test for the creation of the experiment directory structure when only
    create_model is used (programmatic interface); we should create a new, empty target."""

    experiment_dir = "./lammps_atm"
    if path.isdir(experiment_dir):
        rmtree(experiment_dir)

    # create a state with the LAMMPS configuration file
    STATE = State(experiment="lammps_atm")

    # We should be able to create 3 new targets.
    STATE.create_model("add_1", "atm_1", {"25": 10})
    STATE.create_model("add_2", "atm_1", {"25": 20})

    STATE.create_model("add_1", "atm_2", {"25": 30})
    STATE.create_model("add_2", "atm_2", {"25": 40})

    STATE.create_model("add_1", params={"25": 50})
    STATE.create_model("add_2", params={"25": 60})

    # Supply the generator with necessary files to run the simulation
    # and generate the specified models
    base_config = "../../examples/LAMMPS/in.atm"
    GEN = Generator(STATE, model_files=base_config)
    GEN.generate()

    # assert that experiment directory was created
    assert(path.isdir(experiment_dir))
    target_1 = path.join(experiment_dir, "atm_1")
    target_2 = path.join(experiment_dir, "atm_2")
    target_3 = path.join(experiment_dir, "default_target")
    assert(path.isdir(target_1))
    assert(path.isdir(target_2))
    assert(path.isdir(target_3))
    target_model_1 = path.join(target_1, "add_1")
    target_model_2 = path.join(target_1, "add_2")
    target_model_3 = path.join(target_2, "add_1")
    target_model_4 = path.join(target_2, "add_2")
    target_model_5 = path.join(target_3, "add_1")
    target_model_6 = path.join(target_3, "add_2")

    model_dirs = [target_model_1, target_model_2,
                  target_model_3, target_model_4,
                  target_model_5, target_model_6]
    # check for model dir and listed configuration file
    for model in model_dirs:
        assert(path.isdir(model))
        assert(path.isfile(path.join(model, "in.atm")))

    if path.isdir(experiment_dir):
        rmtree(experiment_dir)

def test_overwrite_create_model():
    """Test for the creation of the experiment directory structure when only
    create_model is used (programmatic interface); we should create a new, empty target."""

    experiment_dir = "./lammps_atm"
    if path.isdir(experiment_dir):
        rmtree(experiment_dir)

    STATE = State(experiment="lammps_atm")
    STATE.create_model("add_1", "atm_1", {"25": 10})
    STATE.create_model("add_1", params={"25": 50})

    # Supply the generator with necessary files to run the simulation
    # and generate the specified models
    base_config = "../../examples/LAMMPS/in.atm"
    GEN = Generator(STATE, model_files=base_config)
    GEN.generate()

    try:
        STATE.create_model("add_1", params={"25": 90})
        raise SmartSimError("Model name: add_1 has been incorrectly replaced")
    except SSModelExistsError:
        pass

    try:
        STATE.create_model("add_1", "atm_1", params={"25": 90})
        raise SmartSimError("Model name: add_1 has been incorrectly replaced")
    except SSModelExistsError:
        pass

    assert(path.isdir(experiment_dir))
    target_1 = path.join(experiment_dir, "atm_1")
    target_2 = path.join(experiment_dir, "default_target")
    assert(path.isdir(target_1))
    assert(path.isdir(target_2))

    target_model_1 = path.join(target_1, "add_1")
    target_model_2 = path.join(target_2, "add_1")
    model_dirs = [target_model_1, target_model_2]

    # check for model dir and listed configuration file
    for model in model_dirs:
        assert(path.isdir(model))
        assert(path.isfile(path.join(model, "in.atm")))

    if path.isdir(experiment_dir):
        rmtree(experiment_dir)

def test_gen_select_strategy_user_function():
    """A test of the generator using a user supplied function.
    """

    def raise_error(param_names, param_values):
        raise NotImplementedError

    experiment_dir = "./lammps_atm"
    if path.isdir(experiment_dir):
        rmtree(experiment_dir)

    STATE = State(experiment="lammps_atm")
    param_dict = {"25": [20, 25]}
    STATE.create_target("atm", params=param_dict)

    # Supply the generator with necessary files to run the simulation
    # and generate the specified models
    base_config = "../../examples/LAMMPS/in.atm"
    GEN = Generator(STATE, model_files=base_config)
    GEN.set_strategy(raise_error)
    strategy_failed_out = False
    try:
        GEN.generate()
    except NotImplementedError:
        strategy_failed_out = True

    assert(strategy_failed_out)

    if path.isdir(experiment_dir):
        rmtree(experiment_dir)

def test_gen_select_strategy_user_string():

    experiment_dir = "./lammps_atm"
    if path.isdir(experiment_dir):
        rmtree(experiment_dir)

    STATE = State(experiment="lammps_atm")

    param_dict = {"25": [20, 25]}
    STATE.create_target("atm", params=param_dict)

    base_config = "../../examples/LAMMPS/in.atm"
    GEN = Generator(STATE, model_files=base_config)
    GEN.set_strategy("generation_strategies.raise_error")
    strategy_failed_out = False
    try:
        GEN.generate()
    except NotImplementedError:
        #  We should have successfully failed out.
        strategy_failed_out = True

    assert(strategy_failed_out)
    if path.isdir(experiment_dir):
        rmtree(experiment_dir)

def test_gen_select_strategy_default():

    experiment_dir = "./lammps_atm"
    if path.isdir(experiment_dir):
        rmtree(experiment_dir)

    STATE = State(experiment="lammps_atm")

    param_dict = {"25": [20, 25], "5": [10]}
    STATE.create_target("atm", params=param_dict)

    # Supply the generator with necessary files to run the simulation
    # and generate the specified models
    base_config = "../../examples/LAMMPS/in.atm"
    GEN = Generator(STATE, model_files=base_config)
    GEN.set_strategy("all_perm")
    GEN.generate()
    assert(len(STATE.targets[0]) == 2)

    if path.isdir(experiment_dir):
        rmtree(experiment_dir)

def test_gen_random_strategy():

    experiment_dir = "./lammps_atm"
    if path.isdir(experiment_dir):
        rmtree(experiment_dir)

    STATE = State(experiment="lammps_atm")
    param_dict = {"25": [20, 25], "5": [10]}
    STATE.create_target("atm", params=param_dict)

    base_config = "../../examples/LAMMPS/in.atm"
    GEN = Generator(STATE, model_files=base_config)
    GEN.set_strategy("random")
    GEN.generate(n_models=10)
    assert(len(STATE.targets[0]) == 2)

    if path.isdir(experiment_dir):
        rmtree(experiment_dir)

def test_gen_step_strategy():

    experiment_dir = "./lammps_atm"
    if path.isdir(experiment_dir):
        rmtree(experiment_dir)

    STATE = State(experiment="lammps_atm")
    param_dict = {"25": [20, 25, 30], "5": [10, 20, 30]}
    STATE.create_target("atm", params=param_dict)

    base_config = "../../examples/LAMMPS/in.atm"
    GEN = Generator(STATE, model_files=base_config)
    GEN.set_strategy("step")
    GEN.generate()
    assert(len(STATE.targets[0]) == 3)

    if path.isdir(experiment_dir):
        rmtree(experiment_dir)
