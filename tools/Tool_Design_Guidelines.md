# Tool 设计规范

## 1. 基本规范

1. 所有工具必须使用装饰器语法注册
2. 工具函数必须返回标准格式：
   ```python
   {
       "success": bool,  # 操作是否成功
       "result": any,    # 操作结果数据
       "error": str      # 错误信息(失败时)
   }
   ```

## 2. 工具注册

使用 `@register_tool` 装饰器：

```python
from mcp_server import register_tool

@register_tool(
    tool_name="tool_name",
    description="工具描述",
    parameters={
        "param1": {
            "type": "string", 
            "description": "参数说明"
        }
    },
    timeout=45  # 可选，超时时间(秒)，默认60秒
)
def tool_function(param1: str) -> dict:
    ...
```

## 3. 参数定义

1. 每个参数必须定义类型和描述
2. 支持的基本类型：string, number, boolean, object, array
3. 复杂参数应提供示例

## 4. 错误处理

1. 必须捕获所有异常
2. 错误信息应清晰明确
3. 返回格式：
   ```python
   {
       "success": False,
       "result": None,
       "error": "具体错误信息"
   }
   ```
4. 超时错误会返回：
   ```python
   {
       "success": False,
       "result": None,
       "error": "工具执行超时(45秒)"
   }
   ```

## 5. 代码风格

1. 函数必须有完整的docstring
2. 使用类型注解
3. 保持函数单一职责
4. 重要逻辑添加注释

## 6. 示例

完整工具示例：

```python
from mcp_server import register_tool
from pathlib import Path

@register_tool(
    tool_name="read_file",
    description="读取文件内容",
    parameters={
        "path": {
            "type": "string", 
            "description": "文件路径"
        }
    },
    timeout=30  # 设置30秒超时
)
def read_file(path: str) -> dict:
    """读取文件内容
    
    Args:
        path: 文件路径
        
    Returns:
        dict: 包含success, result, error的标准响应
    """
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return {
                "success": True,
                "result": f.read(),
                "error": None
            }
    except Exception as e:
        return {
            "success": False,
            "result": None,
            "error": f"读取文件失败: {str(e)}"
        }
```

## 7. 最佳实践

1. 工具名称使用snake_case
2. 描述信息简明扼要
3. 参数命名要有意义
4. 复杂工具应拆分为多个小工具
5. 保持工具无状态
6. 根据工具复杂度设置合理的超时时间
