from stable_baselines3 import PPO
from echo_env import EchoEnv

def train_agent():
    env = EchoEnv()
    model = PPO("MlpPolicy", env, verbose=1)
    model.learn(total_timesteps=10000)
    model.save("echo_rl_agent.zip")

if __name__ == "__main__":
    train_agent()