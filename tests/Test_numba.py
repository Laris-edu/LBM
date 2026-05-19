import numpy as np
import numba
from numba import njit
import time

print(f"numpy:  {np.__version__}")
print(f"numba:  {numba.__version__}")

# 测试 1：基本 njit 能编译
@njit
def simple_sum(arr):
    s = 0.0
    for i in range(arr.size):
        s += arr[i]
    return s

x = np.arange(1_000_000, dtype=np.float64)

# 第一次调用会触发 JIT 编译，慢
t0 = time.time()
result1 = simple_sum(x)
t1 = time.time()
print(f"First call (with JIT compile): {t1-t0:.3f} s, result = {result1}")

# 第二次调用使用缓存的编译，应该飞快
t0 = time.time()
result2 = simple_sum(x)
t1 = time.time()
print(f"Second call (cached):          {t1-t0:.6f} s, result = {result2}")

# 测试 2：纯 NumPy 对比
t0 = time.time()
result3 = x.sum()
t1 = time.time()
print(f"NumPy sum:                     {t1-t0:.6f} s, result = {result3}")

# 测试 3：纯 Python for 循环对比（慢得多）
def python_sum(arr):
    s = 0.0
    for i in range(arr.size):
        s += arr[i]
    return s

t0 = time.time()
result4 = python_sum(x)
t1 = time.time()
print(f"Pure Python loop:              {t1-t0:.3f} s, result = {result4}")