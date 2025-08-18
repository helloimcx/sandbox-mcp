# 网络限制功能

## 概述

网络限制功能允许管理员控制 Jupyter kernel 会话的网络访问权限，提供细粒度的安全控制。该功能通过 monkey patching Python 的网络相关函数来实现，可以完全禁用网络访问或仅允许访问特定域名。

## 功能特性

- **完全禁用网络访问**：阻止所有网络连接
- **域名白名单**：仅允许访问指定的域名
- **域名黑名单**：阻止访问特定域名
- **子域名支持**：支持域名和子域名的匹配规则
- **实时配置**：可在运行时动态调整网络限制

## 配置选项

在 `config/config.py` 中添加以下配置项：

```python
class Settings(BaseSettings):
    # 网络访问控制
    enable_network_access: bool = Field(
        default=True,
        description="是否启用网络访问",
        env="ENABLE_NETWORK_ACCESS"
    )
    
    allowed_domains: List[str] = Field(
        default_factory=list,
        description="允许访问的域名列表",
        env="ALLOWED_DOMAINS"
    )
    
    blocked_domains: List[str] = Field(
        default_factory=list,
        description="禁止访问的域名列表",
        env="BLOCKED_DOMAINS"
    )
```

## 环境变量配置

可以通过环境变量来配置网络限制：

```bash
# 禁用网络访问
export ENABLE_NETWORK_ACCESS=false

# 仅允许访问特定域名
export ENABLE_NETWORK_ACCESS=true
export ALLOWED_DOMAINS="google.com,github.com,stackoverflow.com"

# 阻止访问特定域名
export ENABLE_NETWORK_ACCESS=true
export BLOCKED_DOMAINS="facebook.com,twitter.com"
```

## 域名匹配规则

### 白名单规则

1. **精确匹配**：`google.com` 仅匹配 `google.com`
2. **子域名匹配**：`.google.com` 匹配 `google.com` 和所有子域名（如 `mail.google.com`）
3. **域名和子域名**：`google.com` 也会匹配其子域名（如 `mail.google.com`）

### 黑名单规则

黑名单优先级高于白名单。即使域名在白名单中，如果也在黑名单中，仍会被阻止访问。

## API 使用

### 基本函数

```python
from utils.network_restriction import (
    disable_network_access,
    enable_network_access,
    restore_network_access,
    apply_network_restrictions,
    get_network_status
)

# 完全禁用网络访问
disable_network_access()

# 启用网络访问（无限制）
enable_network_access()

# 启用网络访问（仅允许特定域名）
enable_network_access(allowed_domains=['google.com', 'github.com'])

# 启用网络访问（阻止特定域名）
enable_network_access(blocked_domains=['facebook.com', 'twitter.com'])

# 完全恢复网络访问
restore_network_access()

# 获取当前网络状态
status = get_network_status()
print(status)
# {'network_disabled': False, 'allowed_domains': ['google.com'], 'blocked_domains': []}
```

### 配置应用

```python
# 根据配置应用网络限制
apply_network_restrictions(
    enable_network=True,
    allowed_domains=['google.com', 'github.com'],
    blocked_domains=['facebook.com']
)
```

## 在 Kernel 会话中的集成

网络限制会在 kernel 会话启动时自动应用：

```python
# 在 KernelSession.start() 方法中
if hasattr(settings, 'enable_network_access'):
    apply_network_restrictions(
        enable_network=settings.enable_network_access,
        allowed_domains=settings.allowed_domains,
        blocked_domains=settings.blocked_domains
    )
    logger.info(f"Applied network restrictions for session {self.session_id}")
else:
    logger.info(f"Network restrictions not configured for session {self.session_id}")
```

## 错误处理

当网络访问被阻止时，会抛出 `NetworkAccessError` 异常：

```python
from utils.network_restriction import NetworkAccessError

try:
    import socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
except NetworkAccessError as e:
    print(f"网络访问被阻止: {e}")
    # 网络访问被阻止: Network access is disabled for this session. Socket connections are not allowed.
```

## 测试

### 运行网络限制测试

```bash
# 运行所有网络限制测试
pytest tests/unit/test_network_restriction.py -v

# 运行特定测试
pytest tests/unit/test_network_restriction.py::TestNetworkRestriction::test_disable_network_access_blocks_socket_creation -v
```

### 测试覆盖的场景

- Socket 连接阻止
- DNS 查询限制
- HTTP 请求控制
- 域名白名单验证
- 域名黑名单验证
- 网络状态查询
- 配置应用测试
- Kernel 会话集成测试

## 安全注意事项

1. **默认安全**：建议在生产环境中默认禁用网络访问
2. **最小权限原则**：仅允许必要的域名访问
3. **定期审查**：定期检查和更新域名白名单
4. **日志监控**：监控网络访问尝试的日志
5. **测试隔离**：确保测试环境不受网络限制影响

## 故障排除

### 常见问题

1. **测试失败**：确保测试配置正确排除了网络限制测试
2. **配置不生效**：检查环境变量是否正确设置
3. **域名无法访问**：验证域名是否在白名单中且不在黑名单中
4. **意外的网络阻止**：检查 `_network_restrictions_active` 标志状态

### 调试方法

```python
# 检查当前网络状态
from utils.network_restriction import get_network_status
print(get_network_status())

# 检查域名是否被允许
from utils.network_restriction import _is_domain_allowed
print(_is_domain_allowed('google.com'))

# 查看日志
import logging
logging.getLogger('utils.network_restriction').setLevel(logging.DEBUG)
```

## 性能影响

- **最小开销**：仅在网络操作时进行检查
- **内存使用**：域名列表存储在内存中，影响很小
- **CPU 开销**：域名匹配算法高效，性能影响可忽略

## 未来改进

- 支持 IP 地址范围限制
- 添加网络流量监控
- 实现更复杂的访问控制策略
- 支持时间基础的访问控制
- 添加网络访问审计功能