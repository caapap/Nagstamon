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

### 快速开始

## 开发环境部署

- 安装python 依赖
- 建议使用python 3.8.10
- 升级pip

```shell
python -m pip install --upgrade pip -i https://pypi.mirrors.ustc.edu.cn/simple/
```

- 安装pip包

```shell
pip3 install -r build/requirements/windows.txt -i https://pypi.mirrors.ustc.edu.cn/simple/
```

## 使用方法



## 界面介绍

## 架构


## 技术解决案例

## BUG修复


## 参考

### API接口信息

#### n9e 接口配置信息

##### /v1/n9e 类接口

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

具体有哪些接口可以用呢：

中心端 n9e 接收心跳的接口是 [/v1/n9e/heartbeat](https://github.com/caapap/momo/blob/master/conf/n9e-router.go#L375) n9e-edge 接收心跳的接口是 /v1/n9e/edge/heartbeat
接收数据的接口在[这里](https://github.com/caapap/momo/blob/master/conf/n9e-router.go#L41)
第三方调用的接口在[这里](https://github.com/caapap/momo/blob/master/conf/n9e-router.go#L332)






### FAQ

