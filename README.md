# BeRay Python SDK 中文文档

本 SDK 为 BeRay API 提供了一个便捷的 Python 客户端，封装了所有 API 的复杂性，让您可以轻松地与后端服务进行交互。

## 功能特性

*   **完整的 API 覆盖**：支持认证、用户、任务和文件管理的所有端点。
*   **自动化的认证管理**：一次登录，客户端自动处理后续请求的 Token。
*   **健壮的错误处理**：为不同类型的 API 错误定义了清晰的自定义异常。
*   **流式事件支持**：轻松消费来自服务器的实时任务更新 (SSE)。
*   **类型提示**：完整的类型注解，提供更好的代码提示和静态分析。

## 安装

本项目使用 [uv](https://docs.astral.sh/uv/) 进行依赖管理。

1.  克隆或下载项目后，进入项目目录：
    ```bash
    cd beray
    ```
2.  使用 uv 安装依赖：
    ```bash
    uv sync
    ```

## 快速上手

下面是一个简单的示例，展示如何初始化客户端、登录并创建一个新任务。

```python
from beray.client import BeRayClient
from beray.exceptions import APIError

# 1. 初始化客户端
# 假设 BeRay API 运行在 http://localhost:8000
client = BeRayClient(base_url="http://localhost:8000")

try:
    # 2. 登录
    # 在实际应用中，请使用真实的用户凭证
    # 登录成功后，客户端会自动保存 access token
    user_info = client.login("user@example.com", "your_secure_password")
    print(f"登录成功！用户信息: {user_info['user']}")

    # 3. 创建一个新任务
    task_goal = "帮我写一个简单的python脚本打印hello world"
    new_task = client.create_task(goal=task_goal)
    print(f"成功创建任务: ID - {new_task['id']}, 状态 - {new_task['status']}")

    # 4. 列出所有任务
    all_tasks = client.list_tasks()
    print(f"你一共有 {len(all_tasks)} 个任务。")

    # 5. 实时监听任务更新 (可选)
    # 获取刚刚创建任务的ID
    task_id = new_task['id']
    print(f"\n--- 开始监听任务 {task_id} 的更新 ---")
    try:
        for update in client.stream_task_updates(task_id=task_id):
            print(f"收到更新: {update}")
        print(f"--- 任务 {task_id} 的更新流已结束 ---")
    except Exception as e:
        print(f"流式连接出错: {e}")

except APIError as e:
    print(f"发生错误: {e.status_code} - {e.error_detail}")
```

## API 详解

### 客户端初始化

`BeRayClient(base_url: str, token: Optional[str] = None)`

*   `base_url` (str): BeRay API 的基础 URL (例如, `http://localhost:8000`)。
*   `token` (Optional[str]): 可选参数。如果您已经有一个有效的 `access_token`，可以在初始化时直接提供。

```python
from beray.client import BeRayClient

# 基本初始化
client = BeRayClient("http://localhost:8000")

# 使用已有的 token 初始化
client_with_token = BeRayClient(
    base_url="http://localhost:8000",
    token="your_existing_access_token"
)
```

---

### 认证 (Authentication)

客户端会自动处理 `access_token` 的存储和在请求头中的发送。

#### 1. 请求邮箱验证码

`request_verification_code(email: str)`

为新用户注册前，向指定邮箱发送验证码。

```python
client.request_verification_code("new_user@example.com")
# 成功时返回: {'message': '验证码已发送到您的邮箱。请查收。'}
```

#### 2. 注册新用户

`register(email: str, verification_code: str, password: str)`

使用邮箱、验证码和密码注册一个新账户。注册成功后，客户端会自动记录 `access_token` 用于后续请求。

```python
# 假设从邮箱收到了验证码 "123456"
response = client.register(
    email="new_user@example.com",
    verification_code="123456",
    password="a_very_secure_password"
)
print(response['user'])
```

#### 3. 用户登录 (JSON)

`login(email: str, password: str)`

使用邮箱和密码登录。登录成功后，客户端会自动记录 `access_token`。

```python
response = client.login("existing_user@example.com", "my_password")
print(f"欢迎回来, {response['user']['email']}!")
```

#### 4. 用户登录 (OAuth2 表单)

`login_with_form(email: str, password: str)`

使用表单数据 (form data) 进行登录，兼容 OAuth2。

```python
response = client.login_with_form("existing_user@example.com", "my_password")
```

#### 5. 获取当前用户信息

`get_current_user()`

获取当前已认证用户的详细信息。需要先登录。

```python
user = client.get_current_user()
print(f"当前用户ID: {user['id']}, 邮箱: {user['email']}")
```

#### 6. 用户登出

`logout()`

登出当前用户。客户端会清除已保存的 `access_token`。

```python
response = client.logout()
print(response['message']) # '已成功登出'
```

---

### 任务管理 (Task Management)

#### 1. 创建任务

`create_task(goal: str)`

创建一个新的 AI 助手任务。

```python
task = client.create_task(goal="写一首关于宇宙的诗。")
print(f"新任务已创建，ID: {task['id']}")
```

#### 2. 列出所有任务

`list_tasks()`

获取当前用户的所有任务列表。

```python
tasks = client.list_tasks()
for task in tasks:
    print(f"ID: {task['id']}, 目标: {task['goal'][:20]}..., 状态: {task['status']}")
```

#### 3. 获取特定任务详情

`get_task(task_id: int)`

获取指定 ID 任务的详细信息，包括事件列表。

```python
task_details = client.get_task(task_id=1)
print(task_details)
```

#### 4. 实时获取任务更新 (SSE)

`stream_task_updates(task_id: int)`

通过 Server-Sent Events (SSE) 实时流式获取任务的状态和事件更新。这是一个生成器，会产生包含更新信息的字典。

```python
import json

# 假设 client 已经初始化并登录

# 1. 创建一个新任务来监听
task_goal = "1.帮我写一个简单的python脚本打印hello world"
try:
    new_task = client.create_task(goal=task_goal)
    task_id = new_task['id']
    print(f"任务 {task_id} 已创建，开始监听更新...")

    # 2. 实时获取该任务的更新
    for update in client.stream_task_updates(task_id=task_id):
        # update 是一个包含任务状态或事件的字典
        # 使用 json.dumps 美化输出
        print(json.dumps(update, indent=2, ensure_ascii=False))

    print(f"--- 任务 {task_id} 的更新流已结束 ---")

except APIError as e:
    print(f"API 操作失败: {e}")
except Exception as e:
    print(f"流式连接出错: {e}")
```

#### 5. 停止任务

`stop_task(task_id: int)`

请求停止一个正在运行中的任务。

```python
response = client.stop_task(task_id=1)
print(response['message'])
```

#### 6. 删除任务

`delete_task(task_id: int)`

删除指定的任务及其所有相关数据。

```python
response = client.delete_task(task_id=2)
print(response['message'])
```

---

### 任务文件管理 (Task File Management)

#### 1. 列出任务文件树

`list_files_tree(task_id: int, path: str = ".")`

列出指定任务工作目录 (`work_dir`) 内的文件和文件夹结构。

```python
# 列出根目录
file_tree = client.list_files_tree(task_id=1)
print(file_tree)

# 列出子目录 'output'
subdir_tree = client.list_files_tree(task_id=1, path="output")
print(subdir_tree)
```

#### 2. 上传文件

`upload_file(task_id: int, path: str, content: bytes or str, content_type: Optional[str] = None)`

向任务的工作目录中上传或更新一个文件。

```python
# 上传文本内容
client.upload_file(
    task_id=1,
    path="source_code/main.py",
    content="print('Hello, BeRay!')"
)

# 上传二进制内容
with open("my_image.png", "rb") as f:
    client.upload_file(
        task_id=1,
        path="images/my_image.png",
        content=f.read()
    )
```

#### 3. 获取文件内容

`get_file_content(task_id: int, path: str)`

下载任务工作目录中某个文件的内容。返回一个 `requests.Response` 对象。

```python
response = client.get_file_content(task_id=1, path="results/summary.txt")

if response.ok:
    # 将内容保存到本地文件
    with open("local_summary.txt", "wb") as f:
        f.write(response.content)
    print("文件下载成功。")
```

#### 4. 下载文件/文件夹为 ZIP

`download_files_as_zip(task_id: int, paths: Optional[List[str]] = None)`

将任务工作目录中的指定文件/文件夹打包成 ZIP 下载。如果 `paths` 为空，则下载整个工作目录。

```python
# 下载指定的文件和文件夹
response = client.download_files_as_zip(
    task_id=1,
    paths=["results/summary.txt", "images/"]
)

if response.ok:
    with open("task_1_archive.zip", "wb") as f:
        f.write(response.content)
    print("ZIP 归档下载成功。")

# 下载整个工作目录
response = client.download_files_as_zip(task_id=1)
# ...
```

---

### 异常处理 (Exception Handling)

SDK 在遇到 API 错误时会引发特定的异常，所有异常都继承自 `BeRayException`。

*   `BeRayException`: 所有 SDK 异常的基类。
*   `AuthenticationError`: 认证失败 (401, 403)。
*   `NotFoundError`: 资源未找到 (404)。
*   `ConflictError`: 资源冲突 (409)，例如邮箱已注册。
*   `UnprocessableEntityError`: 请求体验证失败 (422)。
*   `APIError`: 其他所有 API 错误 (例如 500)。

您可以这样捕获它们：

```python
from beray.exceptions import ConflictError, APIError

try:
    client.request_verification_code("existing_user@example.com")
except ConflictError as e:
    print(f"操作冲突: {e.error_detail}")
except APIError as e:
    print(f"发生 API 错误: 状态码 {e.status_code}, 详情: {e.error_detail}")
```

## 运行测试

要运行完整的测试套件，请确保已安装开发依赖，然后执行：

```bash
uv run pytest
```
