### 天天生鲜——网页端django项目


环境：

+ WSL2-Ubuntu20.04
+ python3.6
+ requirements.txt

依赖的服务：

+ mysql：用作数据库存储
+ redis：用作会话和缓存存储、celery的broker
+ fastdfs：用作图片存储
+ nginx：用作转发和负载均衡
+ alipay沙箱环境：用作支付服务接口

涉及的技术：

+ nginx+uwsgi+django
  > 通过nginx实现转发和负载均衡
  > 使用django作为后端框架
  > 使用uwsgi部署
+ html/css/js
  > 部分前端模板页面自己编写
+ linux
  > 封装简单的运行shell脚本
  > python项目开发虚拟环境配置
  > mysql、redis、nginx和fastdfs配置
  > git配置及使用
