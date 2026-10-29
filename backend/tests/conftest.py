import os
import tempfile

# 测试使用临时 SQLite 文件，须在导入 app 之前设置
_tmp = tempfile.mkdtemp()
os.environ["STUDYROOM_DATABASE_URL"] = f"sqlite:///{_tmp}/test.db"
