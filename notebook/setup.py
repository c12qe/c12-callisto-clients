"""
basic routines you want to run at the beginning of your notebook
"""
import sys
import pathlib

# this allows you import directly from the src folder.
# Example: from mymodule.utils import do_something_usefull
sys.path.insert(0, str(pathlib.Path(__file__).parents[1] / 'src'))

# here you can import for instance the lib you usually use
# import pandas as pd

# or setup some config for those libs
# pd.set_option('display.max_rows', 500)
# pd.set_option('display.max_columns', 500)
# pd.set_option('display.width', 1000)
