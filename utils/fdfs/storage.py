from django.conf import settings
from django.core.files.storage import Storage
from fdfs_client.client import Fdfs_client


class FDFSStorage(Storage):
    """FastDFS存储类"""

    def __init__(self, client_conf=None, base_url=None):
        if client_conf is None:
            client_conf = settings.FDFS_CLIENT_CONF
        self.client_conf = client_conf
        if base_url is None:
            base_url = settings.FDFS_URL
        self.base_url = base_url

    def _open(self, name, mode='rb'):
        """打开文件时使用"""
        pass

    def _save(self, name, content):
        """存储文件时使用（后台上传），返回文件名group..."""
        client = Fdfs_client(self.client_conf)
        ret = client.upload_by_buffer(content.read())
        if ret.get('Status') != 'Upload successed.':
            raise Exception('上传文件到FastDFS失败')
        return ret.get('Remote file_id')

    def exists(self, name):
        """Django判断文件是否可用（本例中仅上传，文件内容不重复，即可用）"""
        return False

    def url(self, name):
        """返回访问文件的url路径，使用.url时调用"""
        return self.base_url + name
