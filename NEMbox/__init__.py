from .const import Constant
from .utils import create_dir
from .utils import create_file

create_dir(Constant.conf_dir)
create_dir(Constant.download_dir)
create_file(Constant.storage_path)
create_file(Constant.log_path, default="")
create_file(Constant.cookie_path, default="#LWP-Cookies-2.0\n")
