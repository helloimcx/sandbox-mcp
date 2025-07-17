# MCP Server Tests

这个目录包含了 MCP (Model Context Protocol) 服务器的所有测试代码。

## 测试结构

### 主要测试文件

- **`test_mcp_integration.py`** - 集成测试套件
  - 使用官方 MCP streamable HTTP 客户端
  - 测试基本功能、综合功能、错误处理等
  - 包含完整的端到端测试

- **`test_mcp_http.py`** - HTTP 测试套件
  - 直接 HTTP 请求测试
  - JSON-RPC 协议测试
  - 自定义 HTTP 客户端测试

- **`test_runner.py`** - 测试运行器
  - 统一的测试入口点
  - 支持选择性运行测试
  - 提供测试结果汇总

### 现有单元测试

- **`test_api.py`** - API 层单元测试
- **`test_kernel_manager.py`** - 内核管理器单元测试

### 遗留测试文件

以下文件是从项目根目录移动过来的原始测试文件，保留作为参考：

- `test_quick_legacy.py`
- `test_streamable_client_legacy.py`
- `test_simple_mcp_legacy.py`

## 使用方法

### 运行所有测试

```bash
# 从项目根目录运行
cd /Users/yinyin/code/sandbox-mcp
python tests/test_runner.py

# 或者从 tests 目录运行
cd tests
python test_runner.py
```

### 运行特定类型的测试

```bash
# 只运行集成测试
python tests/test_runner.py --tests integration

# 只运行 HTTP 测试
python tests/test_runner.py --tests http

# 运行集成和 HTTP 测试
python tests/test_runner.py --tests integration http

# 快速测试（只运行基本功能测试）
python tests/test_runner.py --quick
```

### 单独运行测试文件

```bash
# 运行集成测试
python tests/test_mcp_integration.py

# 运行 HTTP 测试
python tests/test_mcp_http.py
```

## 测试依赖

### 集成测试依赖

```bash
uv add 'mcp[cli]'
```

### HTTP 测试依赖

```bash
uv add aiohttp
```

## 测试内容

### 集成测试覆盖

1. **基本功能测试**
   - MCP 服务器连接
   - 基本 Python 代码执行
   - 数学计算

2. **综合功能测试**
   - Python 代码执行
   - 数学计算
   - 数据结构和循环
   - 函数定义
   - 会话持久性
   - 错误处理
   - 库导入
   - 会话管理
   - 提示生成
   - 会话清理

3. **Streamable 客户端测试**
   - 连接初始化
   - 工具列表
   - 资源列表
   - 提示列表
   - 工具执行
   - 会话管理

4. **错误处理测试**
   - 无效 Python 代码
   - 无效工具调用

### HTTP 测试覆盖

1. **直接 HTTP 端点测试**
   - 根端点
   - MCP 端点 GET/POST
   - JSON-RPC 协议
   - 工具/资源/提示列表
   - 工具执行

2. **MCP 功能测试**
   - 工具列表
   - Python 代码执行
   - 会话列表
   - Matplotlib 绘图
   - 资源访问
   - 提示生成
   - 会话终止

## 测试环境要求

1. **MCP 服务器运行**
   ```bash
   python run.py --debug
   ```
   服务器应该在 `http://localhost:16010` 运行

2. **Python 环境**
   - Python 3.8+
   - 所需依赖包已安装

3. **网络连接**
   - 本地服务器可访问
   - 无防火墙阻挡

## 故障排除

### 常见问题

1. **连接错误**
   - 确保 MCP 服务器正在运行
   - 检查端口 16010 是否可用
   - 确认服务器地址正确

2. **依赖错误**
   - 运行 `uv add 'mcp[cli]'` 安装 MCP 客户端
   - 运行 `uv add aiohttp` 安装 HTTP 客户端

3. **测试失败**
   - 检查服务器日志
   - 确认所有服务正常运行
   - 查看具体错误信息

### 调试模式

在测试文件中，错误会自动打印堆栈跟踪信息，便于调试。

## 贡献指南

1. **添加新测试**
   - 在相应的测试类中添加新方法
   - 遵循现有的命名约定
   - 添加适当的错误处理

2. **修改现有测试**
   - 保持向后兼容性
   - 更新相关文档
   - 确保所有测试仍能通过

3. **测试最佳实践**
   - 使用描述性的测试名称
   - 添加适当的打印输出
   - 处理异常情况
   - 清理测试资源