# 性能测试文档

本文档介绍如何使用 Sandbox MCP 项目的性能测试功能。

## 概述

性能测试是确保系统在各种负载条件下正常运行的重要环节。本项目提供了全面的性能测试套件，包括：

- **基准测试 (Benchmark Tests)**: 测量关键函数和操作的执行时间
- **内存性能测试 (Memory Tests)**: 监控内存使用情况和内存泄漏
- **负载测试 (Load Tests)**: 模拟多用户并发访问
- **性能分析 (Profiling)**: 识别性能瓶颈

## 快速开始

### 1. 安装依赖

```bash
# 使用 Makefile 安装性能测试依赖
make perf-install

# 或者手动安装
uv sync --group dev
```

### 2. 运行所有性能测试

```bash
make test-performance
```

### 3. 查看测试报告

测试完成后，报告将生成在 `tests/reports/` 目录下：

- `performance_report.html` - 综合性能报告
- `benchmark_results.json` - 基准测试详细结果
- `load_test_report.html` - 负载测试报告

## 详细使用指南

### 基准测试

基准测试用于测量关键操作的执行时间：

```bash
# 运行所有基准测试
make test-benchmark

# 运行特定模式的基准测试
python scripts/run_performance_tests.py --type benchmark --pattern "session_creation"
```

**测试内容：**
- Session 创建性能
- 代码执行性能
- 多会话并发性能
- Session 查找性能
- API 端点响应时间

### 内存性能测试

内存测试监控内存使用情况和检测内存泄漏：

```bash
# 运行内存性能测试
make test-memory
```

**测试内容：**
- Session 创建内存使用
- 长时间运行内存变化
- 内存泄漏检测
- 并发会话内存使用
- 大数据处理内存消耗
- 垃圾回收效果

### 负载测试

负载测试模拟真实用户场景，测试系统在高负载下的表现：

```bash
# 启动服务器（在另一个终端）
make run

# 运行标准负载测试（60秒，10用户）
make test-load

# 运行快速负载测试（30秒，5用户）
make test-load-quick

# 运行重负载测试（300秒，50用户）
make test-load-heavy

# 自定义负载测试
python scripts/run_performance_tests.py --type load --duration 120 --users 20 --spawn-rate 5
```

**负载测试场景：**
- 健康检查
- Session 创建和管理
- 代码执行（简单、数学运算、数据处理）
- 长时间运行代码
- 错误处理
- 管理员操作

### 性能分析

性能分析帮助识别代码中的性能瓶颈：

```bash
# 运行性能分析
make test-profile
```

分析结果将保存在 `tests/reports/profile_results.prof`，可以使用以下命令查看：

```bash
# 查看性能分析结果
python -c "import pstats; p = pstats.Stats('tests/reports/profile_results.prof'); p.sort_stats('cumulative').print_stats(20)"
```

## 性能指标和阈值

### 基准测试阈值

| 操作 | 目标时间 | 警告阈值 | 失败阈值 |
|------|----------|----------|----------|
| Session 创建 | < 100ms | 200ms | 500ms |
| 简单代码执行 | < 500ms | 1s | 2s |
| API 响应 | < 200ms | 500ms | 1s |
| Session 查找 | < 10ms | 50ms | 100ms |

### 内存使用阈值

| 场景 | 目标内存 | 警告阈值 | 失败阈值 |
|------|----------|----------|----------|
| 单个 Session | < 1MB | 5MB | 10MB |
| 100个 Session | < 100MB | 200MB | 500MB |
| 内存泄漏 | < 5MB | 10MB | 20MB |

### 负载测试指标

| 指标 | 目标值 | 可接受值 | 不可接受值 |
|------|--------|----------|------------|
| 平均响应时间 | < 500ms | < 1s | > 2s |
| 95% 响应时间 | < 1s | < 2s | > 5s |
| 错误率 | < 1% | < 5% | > 10% |
| 吞吐量 | > 100 RPS | > 50 RPS | < 20 RPS |

## 测试文件结构

```
tests/performance/
├── __init__.py                     # 包初始化
├── conftest.py                     # 测试配置和 fixtures
├── test_kernel_manager_performance.py  # Kernel Manager 性能测试
├── test_api_performance.py         # API 性能测试
├── test_memory_performance.py      # 内存性能测试
├── locustfile.py                   # Locust 负载测试配置
└── README.md                       # 本文档
```

## 自定义性能测试

### 添加新的基准测试

```python
# 在相应的测试文件中添加
def test_my_function_performance(self, benchmark):
    """测试自定义函数性能。"""
    def my_function():
        # 你的函数逻辑
        return result
    
    result = benchmark(my_function)
    assert result is not None
```

### 添加内存测试

```python
def test_my_memory_usage(self, memory_monitor):
    """测试内存使用情况。"""
    memory_monitor.record("开始")
    
    # 执行操作
    my_operation()
    
    memory_monitor.record("结束")
    memory_monitor.assert_memory_limit(50)  # 限制50MB
```

### 添加负载测试场景

在 `locustfile.py` 中添加新的任务：

```python
@task(5)
def my_custom_task(self):
    """自定义负载测试任务。"""
    self.client.post(
        "/my-endpoint",
        json={"data": "test"},
        name="My Custom Task"
    )
```

## 持续集成 (CI)

在 CI 流水线中集成性能测试：

```bash
# 运行性能 CI 检查（不包括负载测试）
make perf-ci
```

这将运行基准测试和内存测试，但跳过需要运行服务器的负载测试。

## 性能监控和报告

### 生成报告

```bash
# 生成综合性能报告
make perf-report
```

### 报告内容

生成的报告包含：

1. **执行摘要**: 测试运行概况
2. **基准测试结果**: 详细的性能指标
3. **内存使用分析**: 内存消耗和泄漏检测
4. **负载测试结果**: 并发性能表现
5. **性能趋势**: 历史性能对比
6. **优化建议**: 性能改进建议

### 性能回归检测

定期运行性能测试以检测性能回归：

```bash
# 每日性能检查
0 2 * * * cd /path/to/project && make perf-ci
```

## 故障排除

### 常见问题

1. **依赖安装失败**
   ```bash
   # 确保使用正确的 Python 版本
   python --version
   # 手动安装依赖
   pip install pytest-benchmark locust memory-profiler
   ```

2. **负载测试连接失败**
   ```bash
   # 确保服务器正在运行
   curl http://localhost:8000/health
   # 检查端口是否被占用
   lsof -i :8000
   ```

3. **内存测试不稳定**
   ```bash
   # 运行垃圾回收
   python -c "import gc; gc.collect()"
   # 增加测试稳定性
   pytest tests/performance/test_memory_performance.py -v --tb=short
   ```

### 性能调优建议

1. **Session 管理优化**
   - 实现 Session 池
   - 优化 Session 清理逻辑
   - 减少 Session 创建开销

2. **内存优化**
   - 及时释放不需要的对象
   - 使用弱引用避免循环引用
   - 定期执行垃圾回收

3. **API 性能优化**
   - 实现响应缓存
   - 使用异步处理
   - 优化数据序列化

4. **并发性能优化**
   - 使用连接池
   - 实现请求限流
   - 优化锁机制

## 最佳实践

1. **定期运行性能测试**: 在每次重要更改后运行性能测试
2. **设置性能基线**: 建立性能基准，监控性能变化
3. **分层测试**: 从单元级别到系统级别逐层测试
4. **真实场景模拟**: 负载测试应尽可能模拟真实使用场景
5. **性能监控**: 在生产环境中持续监控性能指标
6. **文档更新**: 及时更新性能测试文档和阈值

## 参考资源

- [pytest-benchmark 文档](https://pytest-benchmark.readthedocs.io/)
- [Locust 文档](https://docs.locust.io/)
- [memory-profiler 文档](https://pypi.org/project/memory-profiler/)
- [Python 性能优化指南](https://docs.python.org/3/howto/perf_profiling.html)