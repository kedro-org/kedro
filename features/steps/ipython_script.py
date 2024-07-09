
from IPython.testing.globalipapp import get_ipython
ip = get_ipython()
ip.run_line_magic("load_ext", "kedro.ipython")
# Assume cwd is project root
ip.run_line_magic("reload_kedro", "")
ip.run_line_magic("load_node", "split_data_node")
# ip.rl_next_input is what you see in the terminal input
ip.run_cell(ip.rl_next_input)