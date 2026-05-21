# Phase_1 运行说明

## 当前问题原因

原项目解释器 `.venv` 指向 `Python 3.14 (LBM)`，但该环境在当前工作区内无法正常启动，表现为：

```text
ModuleNotFoundError: No module named 'encodings'
```

这说明 `.venv` 解释器无法找到 Python 标准库，不是 Phase_1 代码本身的数值逻辑错误。

另外，PyCharm 曾有一个卡住的 `pycharm64.exe` 进程占用 IDE 目录锁，导致再次打开时出现 `DirectoryLock` 报错。该进程现在已经不存在，可以重新打开 PyCharm。

## 推荐解释器

已新增一个不破坏原 `.venv` 的 Phase_1 专用环境：

```text
E:\Code\LBM\.venv_phase1\Scripts\python.exe
```

该环境已经验证：

```text
Python 3.12.13
NumPy 2.3.5
```

## PyCharm 设置方式

1. 打开 PyCharm。
2. 进入 `Settings -> Project: LBM -> Python Interpreter`。
3. 选择 `Add Interpreter -> Existing`。
4. 指向：

```text
E:\Code\LBM\.venv_phase1\Scripts\python.exe
```

5. 应用后，不要再使用旧的 `.venv\Scripts\python.exe` 运行 Phase_1。

## 推荐运行入口

不要直接运行 `reference/*.py` 中的模块文件。推荐在 PyCharm 里右键运行以下两个脚本：

```text
scripts/phase1_verify_direct.py
scripts/phase1_generate_reference.py
```

含义：

- `scripts/phase1_verify_direct.py`：运行 Phase_1 的 V0-V5 验证，不依赖 `pytest`。
- `scripts/phase1_generate_reference.py`：重新生成 `results/phase1_reference/` 下的参考 CSV 数据。

## 命令行运行方式

在项目根目录 `E:\Code\LBM` 下运行：

```powershell
.\.venv_phase1\Scripts\python.exe scripts\phase1_verify_direct.py
.\.venv_phase1\Scripts\python.exe scripts\phase1_generate_reference.py
```

当前两条命令均已通过测试。

