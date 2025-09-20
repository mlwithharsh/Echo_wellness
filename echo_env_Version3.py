import gym
from gym import spaces
import numpy as np

class EchoEnv(gym.Env):
    """
    RL environment for EchoV1: State=conversation features, Action=response style, Reward=user feedback/sentiment.
    """
    def __init__(self):
        super(EchoEnv, self).__init__()
        self.observation_space = spaces.Box(low=-5, high=5, shape=(10,), dtype=np.float32)
        self.action_space = spaces.Discrete(3)  # 0: Empathetic, 1: Neutral, 2: Humorous
        self.state = np.zeros(10)
        self.step_count = 0

    def reset(self):
        self.state = np.zeros(10)
        self.step_count = 0
        return self.state

    def step(self, action):
        # Simulate new state (replace with real features)
        self.state = np.random.uniform(-1, 1, size=(10,))
        reward = self.mock_reward(self.state, action)
        self.step_count += 1
        done = self.step_count >= 10
        return self.state, reward, done, {}

    def mock_reward(self, state, action):
        # Example: reward higher if action matches user emotion
        user_emotion = state[0]
        if action == 0:  # empathetic
            return 1.0 if user_emotion < 0 else 0.2
        if action == 2:  # humorous
            return 1.0 if user_emotion > 0 else 0.2
        return 0.5