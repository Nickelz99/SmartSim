import logging
import pickle
import sys
import toml
from os import path, mkdir, listdir
from .helpers import get_SSHOME
from .error import SmartSimError, SSConfigError
from .target import Target
from .model import NumModel
from .orchestrator import Orchestrator
from .smartSimNode import SmartSimNode


class State:
    """The State class holds most of the configurations necessary to run an
       experiment within SmartSim. Upon initialization, State will either
       read and parse the simulation.toml configuration file or will wait
       for the user to call methods to create targets and models.


       :param str experiment: Name of the directory that will house all of
                              the created files and directories. Experiment
                              name can be set in either the simulation.toml
                              or through the state initialization
       :param str config: Name of the configuration file for the experiment
                          The configuration file is optional if the user
                          would rather construct the experiment programmatically
                          in python.
       :param str log_level: Control verbosity of the logger. Options include
                             "DEV", "DEBUG", "INFO", "ERROR".

    """

    def __init__(self, experiment=None, config=None, log_level="DEV"):
        self.current_state = "Initializing"
        self.__create_logger(log_level)
        self._config = self.read_config(config)
        self.targets = []
        self.nodes = []
        self.__set_experiment(experiment)
        self.__init_targets()
        self.orc = None


    def load_target(self, name, target_path=None):
        """Load a pickled target into State for use. The target currently must be from
           the same experiment it originated in. This can be useful if the experiment
           is being conducted over mutliple stages where execution does not all occur
           within the same script.

           :param str name: name of the pickled target
           :param str target_path: Path to the pickled target. Defaults to SMARTSIMHOME

        """
        try:
            tar_dir = path.join(get_SSHOME(), self.experiment, name)
            if target_path:
                tar_dir = target_path
            if path.isdir(tar_dir):
                pickle_file = path.join(tar_dir, name + ".pickle")
                if path.isfile(pickle_file):
                    target = pickle.load(open(pickle_file, "rb"))
                    if target.experiment != self.experiment:
                        err = "Target must be loaded from same experiment \n"
                        msg = "Target experiment: {}   Current experiment: {}".format(target.experiment,
                                                                                       self.experiment)
                        raise SmartSimError(self.current_state, err+msg)
                    self.targets.append(target)
                else:
                    raise SmartSimError(self.current_state,
                                        "Target, {}, could not be found".format(name))
            else:
                raise SmartSimError(self.current_state,
                                     "Target directory could not be found!")
        except SmartSimError as e:
            self.logger.error(e)
            raise


    def create_target(self, name, params={}):
        """Create a target to be used within one or many of the SmartSim Modules. Targets
           keep track of groups of models. Parameters can be given to a target as well in
           order to generate models based on a combination of parameters and generation
           stategies. For more on generation strategies, see the Generator Class.

           :param str name: name of the new target
           :param dict params: dictionary of model parameters to generate models from based
                               on a run strategy.

        """
        try:
            for target in self.targets:
                if target.name == name:
                    raise SmartSimError(self.current_state,
                                         "A target named " + target.name + " already exists!")

            target_path = path.join(get_SSHOME(), self.experiment, name)
            if path.isdir(target_path):
                raise SmartSimError(self.current_state,
                                     "Target directory already exists: " + target_path)
            new_target = Target(name, params, self.experiment, target_path)
            self.targets.append(new_target)
        except SmartSimError as e:
            self.logger.error(e)
            raise

    def create_model(self, name, target, params={}, path=None):
        """Create a model belonging to a specific target. This function is
           useful for running a small number of models where the model files
           are already in place for execution

           :param str name: name of the model to be created
           :param str target: name of the target to place model into
           :param dict params: dictionary of model parameters
           :param str path: (optional) path to model files
        """
        model_added = False
        for t in self.targets:
            if t.name == target:
                model = NumModel(name, params, path)
                t.add_model(model)
                model_added = True
        if not model_added:
            # TODO catch if model already exists
            raise SmartSimError(self.current_state,
                                "Could not find target by the name of: " + target)

    def create_orchestrator(self, name=None, port=6379, nodes=1, ppn=1, duration="1:00:00", **kwargs):
        """Create an orchestrator database to faciliate the transfer of data
           for online training and inference. After the orchestrator is created,
           connections between models and nodes can be instantiated through a
           call to State.register_connection().

           :param str name: name of orchestrator, defaults to "Orchestrator"
           :param int port: the port to open database communications on
           :param int nodes: number of nodes to distribute the database over
                             (currently only works on 1 node)
           :param str duration: how long the orchestrator should run for.
                                format: H:M:S  e.g. "1:00:00"
           """
        settings = kwargs
        settings["nodes"] = nodes
        settings["ppn"] = ppn
        settings["duration"] = duration
        self.orc = Orchestrator(name=name, port=port, **settings)

    def create_node(self, name, script_path=None, **kwargs):
        """Create a SmartSimNode for a specific task. Examples of SmartSimNode
           tasks include training, processing, and inference. Nodes can be used
           to run any task written in any language. The included script/executable
           for nodes often use the Client class to send and recieve data from
           the SmartSim orchestrator.

           :param str name: name of the node to be launched
           :param str script_path: path to the script or executable to be launched.
                                   (default is the current working directory of the
                                    SmartSim run script)
           :param dict kwargs: Extra settings for the workload manager can be set by
                               inluding keyword arguments such as duration="1:00:00"
                               or nodes=5
           """
        # TODO get settings from config file as well
        node = SmartSimNode(name, path=script_path, **kwargs)
        self.nodes.append(node)

    def register_connection(self, sender, reciever):
        """Create a runtime connection in orchestrator for data to be passed between two
           SmartSim entities. The possible types of connections right now are:

                Model -> Node
                Node  -> Node
                Node  -> Model

           :param str sender: name of the created entity with a Client instance to send
                              data to a registered counterpart
           :param str reciever: name of the created entity that will recieve data by
                                making calls to a Client instance.
        """
        if not self.orc:
            raise SmartSimError(self.current_state, "Create orchestrator to register connections")
        else:
            # TODO check if sender and reciever are registered entities
            # TODO check for illegal connection types. e.g. model to model
            self.orc.junction.register(sender, reciever)

    def delete_target(self, name):
        """Delete a created target from State so that any future calls to SmartSim
           Modules will not include this target.

           :param str name: name of the target to be deleted
           :raises SmartSimError: if target doesnt exist
        """
        target_deleted = False
        for t in self.targets:
            if t.name == name:
                self.targets.remove(t)
                target_deleted = True
        if not target_deleted:
            raise SmartSimError(self.current_state,
                                "Could not delete target: " + name)

    def save(self):
        """Save each target currently in state as a pickled python object.
           All models within the target are maintained. Targets can be reloaded
           into an experiment through a call to state.load_target.
        """
        for target in self.targets:
            pickle_path = path.join(target.path, target.name + ".pickle")
            file_obj = open(pickle_path, "wb")
            pickle.dump(target, file_obj)
            file_obj.close()


    def _get_expr_path(self):
        return path.join(get_SSHOME(), self.experiment)


    def __set_experiment(self, experiment_name):
        if not experiment_name:
            try:
                self.experiment = self._get_toml_config(["model", "experiment"])
            except SSConfigError:
                self.logger.error("Experiment name must be defined in either simulation.toml or in state initialization")
                raise
        else:
            self.experiment = experiment_name


    def __init_targets(self):
        """Load targets if they are present within the simulation.toml"""
        if self._config:
            try:
                model_targets = self._get_toml_config(["model", "targets"])
                for target in model_targets:
                    param_dict = self._get_toml_config([target])
                    target_path = path.join(get_SSHOME(), self.experiment, target)
                    new_target = Target(target, param_dict, self.experiment, target_path)
                    self.targets.append(new_target)
            except SSConfigError:
                if model_targets:
                    self.logger.error("No parameter table found for  "+ target+ "e.g. [" + target + "]")
                    raise
                else:
                    self.logger.info("State created without target, target will have to be created or loaded")
        else:
            self.logger.info("State created without target, target will have to be created or loaded")

    def __create_logger(self, log_level):
        import coloredlogs
        logger = logging.getLogger(__name__)
        if log_level == "DEV":
            coloredlogs.install(level=log_level)
        else:
            coloredlogs.install(level=log_level, logger=logger)
        self.logger = logger

    def read_config(self, sim_toml):
        if sim_toml:
            try:
                file_name = get_SSHOME() + sim_toml
                if not path.isfile(file_name):
                    # full path
                    if path.isfile(sim_toml):
                        file_name = sim_toml
                    # neither full path nor SS_HOME
                    else:
                        raise SSConfigError(self.current_state, "Could not find configuration file: " + sim_toml)
                with open(file_name, 'r', encoding='utf-8') as fp:
                    parsed_toml = toml.load(fp)
                    return parsed_toml
            except SSConfigError as e:
                self.logger.error(e)
                raise
            # TODO catch specific toml errors
            except Exception as e:
                self.logger.error(e)
                raise
        else:
            return None

    def _get_toml_config(self, path, none_ok=False):
        """Searches for configurations in the simulation.toml

           Args
             path (list): a list of strings containing path to config
             none_ok (bool): ok for value not to be present

           Returns
             a configuration value if present
             an error if no value/config and none_ok = False
             None if no value/config and none_ok = True
        """
        # Search global configuration file
        if not self._config:
            if none_ok:
                return None
            else:
                raise SSConfigError(self.current_state,
                                "Could not find required SmartSim field: "
                                    + path[-1])
        else:
            try:
                top_level = self.__search_config(path, self._config)
                return top_level
            except SSConfigError as err:
                if none_ok:
                    return None
                else:
                    raise err

    def __search_config(self, value_path, config):
        val_path = value_path.copy()
        # Helper method of _get_config
        if val_path[0] in config.keys():
            if len(val_path) == 1:
                return config[val_path[0]]
            else:
                parent = val_path.pop(0)
                return self.__search_config(val_path, config[parent])
        else:
            raise SSConfigError(self.current_state,
                                "Could not find required SmartSim field: " + value_path[-1])

