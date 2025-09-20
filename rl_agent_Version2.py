from stable_baselines3 import PPO
import numpy as np

class EchoRLAgent:
    def __init__(self, model_path="echo_rl_agent.zip"):
        self.model = PPO.load(model_path)

    def select_action(self, state):
        action, _ = self.model.predict(state, deterministic=True)
        return int(action)