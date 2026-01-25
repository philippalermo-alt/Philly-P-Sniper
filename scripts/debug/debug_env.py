import os
from dotenv import load_dotenv

load_dotenv()

print(f"EMAIL_USER: {os.getenv('EMAIL_USER')}")
print(f"EMAIL_HOST: {os.getenv('EMAIL_HOST')}")

# Check file existence
print(f".env exists: {os.path.exists('.env')}")
with open('.env', 'r') as f:
    for line in f.readlines()[-5:]:
        print(f"Last lines: {line.strip()}")
