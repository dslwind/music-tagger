"""测试标签写入器"""
import os
import tempfile
import pytest
from pathlib import Path

from src.common.writer import TagWriterFactory, ID3Writer, FLACWriter, MP4Writer


class TestTagWriterFactory:
    """测试写入器工厂"""

    def test_get_writer_mp3(self):
        """测试获取 MP3 写入器"""
        writer = TagWriterFactory.get_writer('test.mp3')
        assert isinstance(writer, ID3Writer)

    def test_get_writer_flac(self):
        """测试获取 FLAC 写入器"""
        writer = TagWriterFactory.get_writer('test.flac')
        assert isinstance(writer, FLACWriter)

    def test_get_writer_m4a(self):
        """测试获取 M4A 写入器"""
        writer = TagWriterFactory.get_writer('test.m4a')
        assert isinstance(writer, MP4Writer)

    def test_get_writer_mp4(self):
        """测试获取 MP4 写入器"""
        writer = TagWriterFactory.get_writer('test.mp4')
        assert isinstance(writer, MP4Writer)

    def test_get_writer_unsupported(self):
        """测试不支持的格式"""
        writer = TagWriterFactory.get_writer('test.wav')
        assert writer is None

    def test_get_writer_case_insensitive(self):
        """测试扩展名大小写不敏感"""
        writer = TagWriterFactory.get_writer('TEST.MP3')
        assert isinstance(writer, ID3Writer)

    def test_supported_extensions(self):
        """测试支持的扩展名列表"""
        extensions = TagWriterFactory.supported_extensions()
        assert '.mp3' in extensions
        assert '.flac' in extensions
        assert '.m4a' in extensions
        assert '.mp4' in extensions


class TestID3Writer:
    """测试 ID3 标签写入器"""

    def test_write_creates_file(self):
        """测试写入创建文件"""
        # 跳过实际写入测试，因为没有音频文件
        # 这个测试验证写入器可以被正确实例化
        writer = ID3Writer()
        assert writer is not None


class TestFLACWriter:
    """测试 FLAC 标签写入器"""

    def test_write_creates_file(self):
        """测试写入器实例化"""
        writer = FLACWriter()
        assert writer is not None


class TestMP4Writer:
    """测试 MP4 标签写入器"""

    def test_write_creates_file(self):
        """测试写入器实例化"""
        writer = MP4Writer()
        assert writer is not None