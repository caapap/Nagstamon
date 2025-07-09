## 功能

Nagstamon 是桌面状态监视器。它具有以下主要功能:

- 连接到多个监控服务器

- 驻留在系统托盘中,作为浮动状态栏或全屏在桌面

- 显示关键、警告、未知、无法访问和关闭的主机和服务的简要摘要

- 弹出详细的状态概览当被鼠标指针触摸时

- 连接到显示的主机和服务很容易通过上下文菜单建立

- 动作可以通过 SSH、RDP、VNC 或任何自定义连接触发

- 可以通过声音和闪烁窗口通知用户

- 可以按类别和正则表达式过滤主机和服务

# 1. 开发环境

## 1.1 开发环境部署

- python 3.11.8安装 (推荐使用3.11.x版本且不超过3.11)

```shell
#windows系统下载python-3.11.8-amd64.exe执行程序，安装python环境
https://www.python.org/ftp/python/3.11.8/python-3.11.8-amd64.exe
```

- 升级pip、安装依赖包

```shell
# 使用国内中科大镜像源
python -m pip install --upgrade pip -i https://pypi.mirrors.ustc.edu.cn/simple/
# 根据项目路径下的build/requirements/windows.txt 安装编译所需依赖包
pip3 install -r build/requirements/windows.txt -i https://pypi.mirrors.ustc.edu.cn/simple/
```

## 1.2 编译调试

```shell
python build/build.py
# 若编译过程遇到目录权限访问问题，需要关闭项目代码，之后命令行再次执行编译
# 遇到一些依赖包无法安装情况，需要检查python版本是否正确
# 编译后，在build目录下会生成build和dist目录，dist中包含了软件完整的运行包和.zip压缩包，进入Nagstamon-3.14.0-win64中执行exe程序可进行效果验证。
```

# 2. 架构介绍

​	Nagstamon是用Python 3编写的，并使用Qt 5/6 GUI工具包，这使得它非常可移植。目前适用于GNOME、KDE、Windows和macOS桌面。

## 2.1 项目代码目录介绍

```shell
# Nagstamon的目录结构介绍
./
├── build  // 用于构建项目的脚本和配置文件
├── ChangeLog  // 项目的版本更新日志
├── CONTRIBUTE.md  // 关于如何为项目做贡献的说明
├── COPYRIGHT  // 项目的版权声明
├── LICENSE  // 项目的开源许可证
├── Nagstamon  // Nagstamon的主要源代码目录
├── nagstamon.py  // Nagstamon的主程序入口
├── README.md  // 项目的README文件，一般包含项目的简介，使用和安装方法等
├── SECURITY.md  // 关于项目的安全策略和报告安全问题的方法
├── setup.py // Python项目的构建脚本，用于安装和分发项目
└── tests  // 项目的测试代码

```

## 2.2 项目主模块代码介绍

```shell
# 主模块 Nagstamon 结构：
.
├── Config.py  // 配置相关
├── Helpers.py  // 提供帮助函数
├── __init__.py  // 初始化模块
├── Objects.py  // 定义对象
├── __pycache__  // Python的缓存目录，通常包含编译的Python文件
├── QUI  // QUI模块的目录，包含与图形用户界面相关的代码
├── resources  // 资源目录，包含图像、样式表等静态文件
├── Servers  // 服务器模块的目录，可能包含与服务器交互的代码
└── thirdparty  // 第三方模块的目录，可能包含项目依赖的第三方库的代码
```

# 3. Stellar 二次开发详细实现

## 3.1 技术架构设计

### 3.1.1 继承体系设计
Stellar集成采用了与Prometheus相似的架构设计模式：

```python
# 核心类继承关系
class StellarService(GenericService):
    """Stellar专用服务类，扩展通用服务属性"""
    service_object_id = ""
    labels = {}

class StellarServer(GenericServer):
    """Stellar服务器类，继承通用服务器功能"""
    TYPE = 'Stellar'
    MENU_ACTIONS = ['Monitor']
    API_PATH_ALERTS = "/v1/stellar/alert-cur-events?limit=100"
```

### 3.1.2 与Prometheus架构对比

| 组件 | Prometheus | Stellar | 差异说明 |
|------|------------|---------|----------|
| **API路径** | `/api/v1/alerts` | `/v1/stellar/alert-cur-events?limit=100` | Stellar使用专用API，增加limit参数 |
| **数据结构** | `data["data"]["alerts"]` | `data["dat"]["list"]` | Stellar使用不同的JSON结构 |
| **告警级别** | 字符串形式 | 数字形式(0-3) | Stellar需要数字到字符串映射 |
| **时间格式** | ISO8601 | Unix时间戳 | Stellar需要时间格式转换 |
| **主机名策略** | 直接使用标签 | hash+cluster组合 | Stellar解决同规则折叠问题 |

## 3.2 核心代码实现细节

### 3.2.1 数据获取与解析

```python
def _get_status(self):
    """获取Stellar服务器状态的核心方法"""
    try:
        # 1. API数据获取
        result = self.FetchURL(self.monitor_url + self.API_PATH_ALERTS, giveback="raw")
        data = json.loads(result.result)
        
        # 2. 遍历告警数据 - 关键差异点
        for alert in data["dat"]["list"]:  # 不同于Prometheus的data["data"]["alerts"]
            
            # 3. 告警级别映射 - 核心创新点
            LEVEL_DICT = {
                '1': 'critical',    # 严重
                '2': 'warning',     # 警告  
                '3': 'information', # 信息
                '0': 'NONE'         # 无级别(跳过)
            }
            stellar_severity = alert.get("severity", 0)
            severity = LEVEL_DICT.get(str(stellar_severity), 'unknown').upper()
            
            if severity == "NONE":
                continue
                
            # 4. 主机名唯一性处理 - 解决同规则折叠问题
            hash_part = alert.get('hash', 'unknown')[-4:]
            hostname = f"{hash_part}-{alert.get('cluster', 'unknown')}"
            
            # 5. 时间格式转换 - Unix时间戳转ISO8601
            first_trigger_time = alert.get("first_trigger_time", "N/A")
            if first_trigger_time:
                first_trigger_time = datetime.fromtimestamp(
                    int(first_trigger_time), tz=timezone.utc
                ).isoformat()
                
            service.duration = str(self._get_duration(first_trigger_time))
```

### 3.2.2 状态映射机制

```python
# 告警状态映射
STATE_DICT = {
    '1': 'pending',  # 待处理
    '0': 'firing'    # 触发中
}
stellar_attempt = alert.get("status", 0)
service.attempt = STATE_DICT.get(str(stellar_attempt), "firing")
```

### 3.2.3 信息字段映射

```python
# 状态信息映射 - 复用Prometheus配置
annotations = alert.get("annotations", {})
status_information = ""
for status_information_label in self.map_to_status_information.split(','):
    if status_information_label in annotations:
        status_information = annotations.get(status_information_label)
        break
service.status_information = status_information
```

## 3.3 前端UI集成实现

### 3.3.1 易变组件配置

在`Nagstamon/QUI/__init__.py`中，Stellar被添加到VOLATILE_WIDGETS系统：

```python
self.VOLATILE_WIDGETS = {
    # Stellar复用Prometheus和Alertmanager的配置字段
    self.window.label_map_to_hostname: ['Prometheus', 'Alertmanager', 'Stellar'],
    self.window.input_lineedit_map_to_hostname: ['Prometheus', 'Alertmanager', 'Stellar'],
    self.window.label_map_to_servicename: ['Prometheus', 'Alertmanager', 'Stellar'],
    self.window.input_lineedit_map_to_servicename: ['Prometheus', 'Alertmanager', 'Stellar'],
    self.window.label_map_to_status_information: ['Prometheus', 'Alertmanager', 'Stellar'],
    self.window.input_lineedit_map_to_status_information: ['Prometheus', 'Alertmanager', 'Stellar'],
}
```

### 3.3.2 功能限制配置

```python
# Stellar与Prometheus、Alertmanager共享功能限制
PROMETHEUS_OR_ALERTMANAGER_OR_STELLAR = ['Alertmanager', 'Prometheus', 'Stellar']
NOT_PROMETHEUS_OR_ALERTMANAGER_OR_STELLAR = [x.TYPE for x in SERVER_TYPES.values() 
                                         if x.TYPE not in PROMETHEUS_OR_ALERTMANAGER_OR_STELLAR]

# 这些功能对Stellar不可用
self.VOLATILE_WIDGETS = {
    self.window.input_checkbox_sticky_acknowledgement: NOT_PROMETHEUS_OR_ALERTMANAGER_OR_STELLAR,
    self.window.input_checkbox_send_notification: NOT_PROMETHEUS_OR_ALERTMANAGER_OR_STELLAR,
    self.window.input_checkbox_persistent_comment: NOT_PROMETHEUS_OR_ALERTMANAGER_OR_STELLAR,
    self.window.input_checkbox_acknowledge_all_services: NOT_PROMETHEUS_OR_ALERTMANAGER_OR_STELLAR
}
```

## 3.4 配置系统集成

### 3.4.1 服务器类型注册

在`Nagstamon/Servers/__init__.py`中注册Stellar服务器：

```python
# 导入Stellar服务器类
from Nagstamon.Servers.Stellar import StellarServer

# 服务器列表注册
servers_list = [
    AlertmanagerServer,
    CentreonServer,
    # ... 其他服务器类型
    StellarServer,  # 新增Stellar支持
    # ... 更多服务器类型
]

# 配置字段传递 - 复用Prometheus配置
new_server.map_to_hostname = server.map_to_hostname
new_server.map_to_servicename = server.map_to_servicename  
new_server.map_to_status_information = server.map_to_status_information
```

### 3.4.2 默认配置字段

在`Nagstamon/Config.py`中定义默认映射配置：

```python
class Server(object):
    def __init__(self):
        # Stellar复用Prometheus/Alertmanager配置字段
        self.map_to_hostname = "cluster,group_name,pod_name,namespace,instance"
        self.map_to_servicename = "rule_name,alertname"
        self.map_to_status_information = "chsDesc,summary,description,message"
```

## 3.5 关键技术创新点

### 3.5.1 主机名唯一性解决方案

**问题**：Stellar平台存在同源下同规则折叠问题，如kafka三个topics告警会被折叠显示。

**解决方案**：
```python
# 原始方案（有问题）
# hostname = alert.get('cluster', 'unknown')

# 优化方案：hash后四位 + cluster 确保唯一性
hash_part = alert.get('hash', 'unknown')[-4:]
hostname = f"{hash_part}-{alert.get('cluster', 'unknown')}"
```

**效果**：每个告警规则都有唯一的主机名标识，避免了告警折叠问题。

### 3.5.2 时间格式标准化

**问题**：Stellar返回Unix时间戳，前端需要ISO8601格式。

**解决方案**：
```python
if first_trigger_time:
    first_trigger_time = datetime.fromtimestamp(
        int(first_trigger_time), tz=timezone.utc
    ).isoformat()
service.duration = str(self._get_duration(first_trigger_time))
```

### 3.5.3 数据量限制优化

**问题**：前端告警列表最大显示25条限制。

**解决方案**：
```python
API_PATH_ALERTS = "/v1/stellar/alert-cur-events?limit=100"
```

通过API参数限制，避免前端数据量过大导致的性能问题。

## 3.6 浏览器URL配置

```python
BROWSER_URLS = {
    'monitor':  '$MONITOR$/dashboards',     # 仪表板
    'hosts':    '$MONITOR$/targets',        # 目标主机
    'services': '$MONITOR$/alert-cur-events', # 当前告警
    'history':  '$MONITOR$/alert-his-events'  # 历史告警
}
```

## 3.7 代码开发流程总结

### 3.7.1 源码评估结论

通过对比prometheus、alertmanager、Stellar活跃告警接口数据，确定复用prometheus源码进行Stellar模块开发的可行性：

1. **技术基础**：Stellar平台使用prometheus进行监控，告警模块基于prometheus二次开发
2. **数据格式**：Stellar页面告警列表和prometheus页面告警列表格式相近
3. **API兼容**：Stellar提供/v1/stellar类型接口，支持BasicAuth密钥认证
4. **数据获取**：通过/v1/stellar/alert-cur-events接口获取告警数据

### 3.7.2 实现策略

1. **继承复用**：继承GenericServer基类，复用核心功能
2. **配置共享**：与Prometheus共享map_to_*配置字段
3. **差异化处理**：针对Stellar特有的数据格式进行适配
4. **UI集成**：最小化UI改动，复用现有组件系统

# 4. 参考

## 4.1.API接口（/v1/stellar )

这类接口其实又分成 2 小类：

- 给 agent 使用，用于 agent 上报心跳信息或者接收监控数据，通常用于内网不加密钥认证
- 给第三方调用的接口，通常会走密钥认证
  这 2 类接口都是走的 BasicAuth 认证，通过配置文件里下面的部分来控制：

```yaml
[HTTP.APIForAgent]
Enable = true 
# [HTTP.APIForAgent.BasicAuth]
# user001 = "ccc26da7b9aba533cbb263a36c07dcc5"

[HTTP.APIForService]
Enable = true 
[HTTP.APIForService.BasicAuth]
user001 = "ccc26da7b9aba533cbb263a36c07dcc5"
```

- 中心端 stellar 接收心跳的接口是 [/v1/stellar/heartbeat](https://github.com/ccfos/nightingale/blob/main/center/router/router.go#L375) stellar-edge 接收心跳的接口是 `/v1/stellar/edge/heartbeat`
- 接收数据的接口参考：[router.go](https://github.com/ccfos/nightingale/blob/main/pushgw/router/router.go#L41)
- 第三方调用的接口参考：[router.go](https://github.com/ccfos/nightingale/blob/main/center/router/router.go#L332)

## 4.2.数据表结构

- alert_rule 是Stellar平台告警规则的记录表，根据配置中的 PromQL 去查询时序数据库，通过多种条件过滤，最终条件符合后生成告警事件 alert_cur_evernt，参考：[table_schema](https://flashcat.cloud/docs/content/flashcat-monitor/nightingale-v6/schema/alert_rule/)

# 5. Bugfixes

- [fixed]告警级别不按照内置级别显示问题
- [fixed]告警时间间隔格式错误问题  
- [fixed]告警列表显示数最大为25条的问题
- [fixed]告警列表在同主机名同告警名时的折叠问题
- [fixed]告警规则对应描述信息实例ip变量无法正常显示问题
- [issue]Last Check字段无法获取值，无法得到上次检查时间
- [issue]浮窗状态下，告警规则无法显示级别为down，目前仅支持information、warning、critical、unknown、error等




