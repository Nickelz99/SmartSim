from smartsim import Controller, Generator, State

STATE = State("/MOM6/simulation.toml", log_level="DEBUG")

# Data Generation Phase
GEN = Generator(STATE)
GEN.generate()

SIM = Controller(STATE, duration="10:00:00")
SIM.start()
SIM.poll()