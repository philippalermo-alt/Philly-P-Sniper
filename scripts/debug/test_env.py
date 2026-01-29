print("Start...")
try:
    import pandas as pd
    print(f"Pandas version: {pd.__version__}")
except ImportError as e:
    print(f"ImportError: {e}")
except Exception as e:
    print(f"Exception: {e}")
print("End.")
