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

- python 3.8.10安装

```shell
#windows系统下载python-3.8.10-amd64.exe执行程序，安装python环境
https://www.python.org/ftp/python/3.8.10/python-3.8.10-amd64.exe
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



# 3. 代码开发流程

## 3.1 源码评估

通过对比prometheus、alertmanager、N9e活跃告警接口数据，可复用prometheus源码，进行N9e的模块开发。原因如下：

```shell
1. N9e平台使用prometheus进行监控，告警模块属于prometheus基础上进行二次开发
2. N9e页面告警列表和prometheus页面告警列表格式相近
3. N9e平台提供了第三方调用的接口/v1/n9e类型，支持走BasicAuth的密钥认证，通过/v1/n9e/alert-cur-events静态接口数据，可进行后端数据调用
```

## 3.2 源码二次开发

[新增]:N9e.py


- case1

```python
# 新增N9eServer服务器类型
class N9eServer(GenericServer):
    """
    special treatment for N9e API
    """
    TYPE = 'N9e'

    # N9e actions are limited to visiting the monitor for now
    MENU_ACTIONS = ['Monitor']
    # 修改页面快捷方式对应地址为N9e实际地址
    BROWSER_URLS = {
        'monitor':  '$MONITOR$/dashboards',
        'hosts':    '$MONITOR$/targets',
        'services': '$MONITOR$/alert-cur-events',
        'history':  '$MONITOR$/alert-his-events'
    }
    # 修改API_PATH_ALERTS活跃告警接口地址，并配置单页条数，放置前端隐藏覆盖
    API_PATH_ALERTS = "/v1/n9e/alert-cur-events?limit=100"
```

- case2

  ```python
  #根据接口数据维度，修改数组元数据变量
  for alert in data["dat"]["list"]:
  	if conf.debug_mode:
  		self.Debug(
  			server=self.get_name(),
  			debug="Processing Alert: " + pprint.pformat(alert)
  		)
  ```

- case3

  ```python
  # 定义字典映射关系，对应项目主模块前端告警级别
  LEVEL_DICT = {
  '1': 'critical',
  '2': 'warning',
  '3': 'information',
  '0': 'NONE'
  }
  n9e_severity = alert.get("severity", 0)
  severity = LEVEL_DICT.get(str(n9e_severity), 'unknown').upper()
  
  if severity == "NONE":
  	continue
  ```

- case4

  ```shell
  # 实际主机名为三平台告警源，根据for循环，依次层级为host-> servicename，因此存在同源下同规则折叠问题（例如kafka三topics告警规则折叠问题），因此需要将host字段进行唯一性处理，处理方法为<hash后四位>+<cluster>字段进行赋值
  
  #hostname = alert.get('id', 'unknown')
  #hostname = alert.get('cluster', 'unknown')
  hash_part = alert.get('hash', 'unknown')[-4:]
  hostname = f"{hash_part}-{alert.get('cluster', 'unknown')}"
  S
  servicename = alert.get('rule_name', 'unknown')
  ```

- case 5

  ```shell
  # 因N9e接口数据中首次触发时间字段为Unix格式，与前端显示的iso格式不一致，这里做格式转换
  if first_trigger_time :
  	first_trigger_time = datetime.fromtimestamp(int(first_trigger_time), tz=timezone.utc).isoformat()
  
  service.duration = str(self._get_duration(first_trigger_time))
  ```

[修改]:Nagstamon/Servers/__init__.py
- case1

  ```python
  # 主模块中，在Nagstamon/Servers/__init__.py 新增N9e类型，对应相关模块初始化操作
  from Nagstamon.Servers.N9e import N9eServer
  ···
  servers_list = [···
                  N9eServer,
                  ···]
  
  ```
[修改]:Nagstamon/QUI/__init__.py
- case1

  ```python
  # 前端模块，的Nagstamon/QUI/__init__.py文件中，添加N9e为新的“易变组件”（VOLATILE_WIDGETS），用来关联前端文本，和相应便签匹配的动态内容
  self.VOLATILE_WIDGETS = {···
  	self.window.label_map_to_hostname: ['Prometheus', 'Alertmanager', 'N9e'],
  	self.window.input_lineedit_map_to_hostname: ['Prometheus', 'Alertmanager', 'N9e'],
  	self.window.label_map_to_servicename: ['Prometheus', 'Alertmanager', 'N9e'],
  	self.window.input_lineedit_map_to_servicename: ['Prometheus', 'Alertmanager', 'N9e'],
  	self.window.label_map_to_status_information: ['Prometheus', 'Alertmanager' , 'N9e'],
  	self.window.input_lineedit_map_to_status_information: ['Prometheus', 'Alertmanager', 'N9e'],
  ```
[修改]:Nagstamon/config.py
- case1

  ```shell
  # Nagstamon/config.py 通用的公共配置文件代码中，新建全局静态变量字段，用于json数据的标签匹配和筛选
  self.map_to_hostname = "cluster,group_name,pod_name,namespace,instance"
  self.map_to_servicename = "rule_name,alertname"
  self.map_to_status_information = "chsDesc,summary,description,message"
  ```


# 4. 参考

## 4.1.API接口（/v1/n9e )

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

- 中心端 n9e 接收心跳的接口是 [/v1/n9e/heartbeat](https://github.com/ccfos/nightingale/blob/main/center/router/router.go#L375) n9e-edge 接收心跳的接口是 `/v1/n9e/edge/heartbeat`
- 接收数据的接口参考：[router.go](https://github.com/ccfos/nightingale/blob/main/pushgw/router/router.go#L41)
- 第三方调用的接口参考：[router.go](https://github.com/ccfos/nightingale/blob/main/center/router/router.go#L332)

## 4.2.数据表结构

- alert_rule 是夜莺平台告警规则的记录表，根据配置中的 PromQL 去查询时序数据库，通过多种条件过滤，最终条件符合后生成告警事件 alert_cur_evernt，参考：[table_schema](https://flashcat.cloud/docs/content/flashcat-monitor/nightingale-v6/schema/alert_rule/)

# 5. Bugfixes

- [fixed]告警级别不按照内置级别显示问题
- [fixed]告警时间间隔格式错误问题
- [fixed]告警列表显示数最大为25条的问题
- [fixed]告警列表在同主机名同告警名时的折叠问题
- [fixed]告警规则对应描述信息实例ip变量无法正常显示问题
- [issue]Last Check字段无法获取值，无法得到上次检查时间
- [issue]浮窗状态下，告警规则无法显示级别为down，目前仅支持information、warning、critical、unknown、error等
