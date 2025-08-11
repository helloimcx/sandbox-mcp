# 项目开发规则 - 测试驱动开发 (TDD)

## 概述
Makefile集成了很多常用的开发命令，如服务启动、测试、打包等。
本项目采用测试驱动开发（Test-Driven Development, TDD）方法论，确保代码质量、可维护性和功能正确性。

## TDD 开发流程

### 1. 红-绿-重构循环

**红阶段（Red）**：
- 编写一个失败的测试用例
- 测试应该描述期望的功能行为
- 运行测试，确认测试失败（红色状态）

**绿阶段（Green）**：
- 编写最少的代码使测试通过
- 不关注代码质量，只关注功能实现
- 运行测试，确认测试通过（绿色状态）

**重构阶段（Refactor）**：
- 改进代码质量，消除重复
- 保持测试通过的前提下优化代码结构
- 运行所有测试，确保重构没有破坏功能

### 2. 开发步骤

1. **需求分析**：明确功能需求和验收标准
2. **编写测试**：先写测试用例，定义期望行为
3. **运行测试**：确认测试失败
4. **实现功能**：编写最小可行代码
5. **运行测试**：确认测试通过
6. **重构代码**：优化代码质量
7. **回归测试**：确保所有测试通过
8. **重复循环**：继续下一个功能

## 测试规范

### 测试文件组织

```
tests/
├── unit/                    # 单元测试
│   ├── test_kernel_manager.py
│   ├── test_session_config.py
│   └── test_file_utils.py
├── integration/             # 集成测试
│   ├── test_api_integration.py
│   └── test_mcp_integration.py
├── e2e/                     # 端到端测试
│   └── test_full_workflow.py
└── fixtures/                # 测试数据
    ├── sample_files/
    └── mock_data/
```

### 测试命名规范

- **测试文件**：`test_<模块名>.py`
- **测试类**：`Test<功能名>`
- **测试方法**：`test_<具体行为>_<预期结果>`

示例：
```python
class TestKernelManager:
    def test_create_session_with_valid_id_returns_session(self):
        pass
    
    def test_create_session_with_duplicate_id_raises_error(self):
        pass
```

### 测试覆盖率要求

- **单元测试覆盖率**：≥ 90%
- **集成测试覆盖率**：≥ 80%
- **关键路径覆盖率**：100%

### 测试类型

#### 1. 单元测试（Unit Tests）
- 测试单个函数或方法
- 使用 mock 隔离依赖
- 快速执行（< 100ms）
- 覆盖边界条件和异常情况

#### 2. 集成测试（Integration Tests）
- 测试组件间交互
- 测试 API 端点
- 测试数据库操作
- 测试文件系统操作

#### 3. 端到端测试（E2E Tests）
- 测试完整用户场景
- 测试系统整体功能
- 模拟真实使用环境

## 代码质量标准

### 1. 测试质量

- **可读性**：测试名称清晰描述测试意图
- **独立性**：每个测试独立运行，不依赖其他测试
- **可重复性**：测试结果一致，不受环境影响
- **快速性**：单元测试执行时间短

### 2. 代码质量

- **SOLID 原则**：遵循面向对象设计原则
- **DRY 原则**：避免代码重复
- **KISS 原则**：保持代码简单
- **YAGNI 原则**：不实现不需要的功能

### 3. 文档要求

- **函数文档**：所有公共函数必须有文档字符串
- **类文档**：所有类必须有用途说明
- **API 文档**：所有 API 端点必须有文档
- **README**：项目根目录必须有完整的 README

## 工具和框架

### 测试框架
- **pytest**：主要测试框架
- **pytest-asyncio**：异步测试支持
- **pytest-cov**：测试覆盖率
- **pytest-mock**：模拟对象

### 代码质量工具
- **black**：代码格式化
- **flake8**：代码风格检查
- **mypy**：类型检查
- **isort**：导入排序

### CI/CD 集成
- 每次提交自动运行测试
- 测试失败阻止合并
- 覆盖率报告自动生成
- 代码质量检查自动执行

## 最佳实践

### 1. 测试编写

```python
# 好的测试示例
def test_create_session_with_valid_parameters_returns_session():
    # Arrange
    session_id = "test-session-123"
    kernel_manager = KernelManagerService()
    
    # Act
    session = await kernel_manager.create_session(session_id)
    
    # Assert
    assert session.session_id == session_id
    assert session.is_active is True
    assert session.kernel_client is not None
```

### 2. Mock 使用

```python
@pytest.fixture
def mock_kernel_manager():
    with patch('src.services.kernel_manager.AsyncKernelManager') as mock:
        yield mock

def test_session_creation_with_mocked_kernel(mock_kernel_manager):
    # 使用 mock 隔离外部依赖
    pass
```

### 3. 异步测试

```python
@pytest.mark.asyncio
async def test_async_function():
    result = await some_async_function()
    assert result is not None
```

### 4. 参数化测试

```python
@pytest.mark.parametrize("input_value,expected", [
    ("valid_input", True),
    ("invalid_input", False),
    ("", False),
])
def test_validation_function(input_value, expected):
    result = validate_input(input_value)
    assert result == expected
```

## 开发工作流

### 1. 功能开发流程

1. **创建分支**：`git checkout -b feature/new-feature`
2. **编写测试**：先写失败的测试
3. **实现功能**：编写最小可行代码
4. **运行测试**：`pytest tests/`
5. **重构代码**：优化代码质量
6. **提交代码**：`git commit -m "feat: add new feature"`
7. **推送分支**：`git push origin feature/new-feature`
8. **创建 PR**：提交 Pull Request

### 2. Bug 修复流程

1. **重现 Bug**：编写失败的测试重现问题
2. **修复代码**：修改代码使测试通过
3. **回归测试**：确保修复没有引入新问题
4. **提交修复**：提交代码和测试

### 3. 重构流程

1. **确保测试覆盖**：重构前确保有足够测试
2. **小步重构**：每次只重构一小部分
3. **频繁测试**：每次修改后运行测试
4. **保持功能不变**：重构不改变外部行为

## 性能测试

### 1. 基准测试
- 使用 `pytest-benchmark` 进行性能测试
- 监控关键函数执行时间
- 设置性能基线和阈值

### 2. 负载测试
- 测试系统在高负载下的表现
- 使用 `locust` 或 `artillery` 进行负载测试
- 监控内存使用和响应时间

## 安全测试

### 1. 输入验证测试
- 测试所有用户输入的验证
- 包括 SQL 注入、XSS 等安全漏洞测试
- 使用 `bandit` 进行安全代码扫描

### 2. 权限测试
- 测试 API 权限控制
- 测试会话隔离
- 测试文件访问权限

## 监控和报告

### 1. 测试报告
- 自动生成测试覆盖率报告
- 生成 HTML 格式的详细报告
- 集成到 CI/CD 流水线

### 2. 质量指标
- 代码覆盖率趋势
- 测试执行时间趋势
- Bug 发现和修复时间
- 代码复杂度指标



