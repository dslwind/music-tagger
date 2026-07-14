"""测试元数据合并逻辑"""
import pytest
from src.applemusic.finder import merge_metadata


class TestMergeMetadata:
    """测试元数据合并"""

    def test_remote_overwrites_local(self):
        """测试远程值覆盖本地值"""
        local = {'title': 'Local Title', 'artist': 'Local Artist'}
        remote = {'title': 'Remote Title', 'artist': 'Remote Artist'}
        result = merge_metadata(local, remote)
        assert result['title'] == 'Remote Title'
        assert result['artist'] == 'Remote Artist'

    def test_local_preserved_when_remote_empty(self):
        """测试远程为空时保留本地值"""
        local = {'title': 'Local Title', 'artist': 'Local Artist'}
        remote = {'title': '', 'artist': ''}
        result = merge_metadata(local, remote)
        assert result['title'] == 'Local Title'
        assert result['artist'] == 'Local Artist'

    def test_both_empty_returns_empty(self):
        """测试两者都为空时返回空"""
        local = {'title': '', 'artist': ''}
        remote = {'title': '', 'artist': ''}
        result = merge_metadata(local, remote)
        assert result['title'] == ''
        assert result['artist'] == ''

    def test_whitespace_handling(self):
        """测试空白字符处理"""
        local = {'title': '  Local  ', 'artist': 'Artist'}
        remote = {'title': '  ', 'artist': '  Remote  '}
        result = merge_metadata(local, remote)
        # 远程只有空白，应保留本地
        assert result['title'] == 'Local'
        # 远程有值，使用远程
        assert result['artist'] == 'Remote'

    def test_partial_update(self):
        """测试部分更新"""
        local = {
            'title': 'Song Title',
            'artist': 'Old Artist',
            'album': '', 'composer': '', 'lyricist': '', 'copyright': ''
        }
        remote = {
            'title': 'New Title',
            'artist': '',
            'album': 'New Album',
            'composer': 'Composer',
            'lyricist': '',
            'copyright': ''
        }
        result = merge_metadata(local, remote)
        assert result['title'] == 'New Title'  # 远程覆盖
        assert result['artist'] == 'Old Artist'  # 远程为空，保留本地
        assert result['album'] == 'New Album'  # 远程新增
        assert result['composer'] == 'Composer'  # 远程新增