import os
import pytest
import time

from smartsim import State, Controller, Generator
from distutils import dir_util
from shutil import which, copyfile, rmtree

# Comment to run profiling tests
#pytestmark = pytest.mark.skip()

# control wether the test runs with a database cluster or not
CLUSTER=True

def test_one_way():
    """test the latency for a sending a vector, a matrix, and a 3D tensor
       from a simulation model to a SmartSimNode"""
    run_test("one-way")

def test_full_loop():
    """test the latency for a sending a vector, a matrix, and a 3D tensor
       from a simulation model to a SmartSimNode and then back to a model"""
    run_test("full-loop")

def test_node_sink():
    """test the latency for a sending a vector, a matrix, and a 3D tensor
       from two simulation models to a single SmartSimNode"""
    run_test("node-sink")

def run_test(test):
    # test data sizes, and ID
    # literal eval is used to create sizes
    data = ["'(200,)'", "'(200,200)'", "'(200, 200, 200)'"]
    test_ids = ["_1D", "_2D", "_3D"]

    # see if we are on slurm machine
    if not which("srun"):
        pytest.skip()
    cluster_size = 1
    if CLUSTER:
        cluster_size = 3
    for data_size, test_id in zip(data, test_ids):
        num_packets = 20
        if test == "one-way":
            run_one_way(data_size, num_packets, test_id, cluster_size)
        elif test == "full-loop":
            run_full_loop(data_size, num_packets, test_id, cluster_size)
        else:
            run_node_sink(data_size, num_packets, test_id, cluster_size)

def run_one_way(data_size, num_packets, test_id, cluster_size):
    experiment_dir = "".join(("one-way", test_id, "/"))
    state = State(experiment=experiment_dir)

    node_settings = {
        "nodes": 1,
        "executable": "python node.py",
    }
    sim_dict = {
        "executable": "python simulation.py",
        "nodes": 1,
        "exe_args": create_exe_args(data_size, num_packets)
    }
    state.create_node("node",
                      run_settings=node_settings)
    state.create_model("sim",
                       run_settings=sim_dict)
    state.create_orchestrator(cluster_size=cluster_size)
    state.register_connection("sim", "node")

    # generate experiment directory
    generator = Generator(state,
                          model_files="./one-way/simulation.py")
    generator.generate()
    copyfile(os.getcwd() + "/one-way/node.py",
             experiment_dir + "node.py")

    control = Controller(state, launcher="slurm")
    control.start()
    while not control.finished():
        time.sleep(2)
    control.release()

    if os.path.isdir(experiment_dir):
        rmtree(experiment_dir)

def run_full_loop(data_size, num_packets, test_id, cluster_size):
    experiment_dir = "".join(("full-loop", test_id, "/"))
    state = State(experiment=experiment_dir)

    node_settings = {
        "nodes": 1,
        "executable": "python node.py",
    }
    sim_dict = {
        "executable": "python simulation.py",
        "nodes": 1,
        "exe_args": create_exe_args(data_size, num_packets)
    }
    state.create_node("node",
                      run_settings=node_settings)
    state.create_model("sim",
                       run_settings=sim_dict)
    state.create_orchestrator(cluster_size=cluster_size)
    state.register_connection("sim", "node")
    state.register_connection("node", "sim")

    # generate experiment directory
    generator = Generator(state,
                          model_files="./full-loop/simulation.py")
    generator.generate()
    copyfile(os.getcwd() + "/full-loop/node.py",
             experiment_dir + "node.py")

    control = Controller(state, launcher="slurm")
    control.start()
    while not control.finished():
        time.sleep(2)
    control.release()

    if os.path.isdir(experiment_dir):
        rmtree(experiment_dir)

def run_node_sink(data_size, num_packets, test_id, cluster_size):
    experiment_dir = "".join(("node-sink", test_id, "/"))
    state = State(experiment=experiment_dir)

    node_settings = {
        "nodes": 1,
        "executable": "python node.py",
    }
    sim_dict = {
        "executable": "python simulation.py",
        "nodes": 1,
        "exe_args": create_exe_args(data_size, num_packets)
    }
    state.create_node("node",
                      run_settings=node_settings)
    state.create_model("sim_1",
                       run_settings=sim_dict)
    state.create_model("sim_2",
                       run_settings=sim_dict)
    state.create_orchestrator(cluster_size=cluster_size)
    state.register_connection("sim_1", "node")
    state.register_connection("sim_2", "node")

    # generate experiment directory
    generator = Generator(state,
                          model_files="./node-sink/simulation.py")
    generator.generate()

    copyfile(os.getcwd() + "/node-sink/node.py",
             experiment_dir + "node.py")

    control = Controller(state, launcher="slurm")
    control.start()
    while not control.finished():
        time.sleep(2)
    control.release()

    if os.path.isdir(experiment_dir):
        rmtree(experiment_dir)


def create_exe_args(data_size, num_packets):
    size = "--size=" + str(data_size)
    num_pack = "--num_packets=" + str(num_packets)
    return " ".join((size, num_pack))