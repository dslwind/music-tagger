"""元数据处理模块 - 管理音频元数据模型和操作"""

from .models import AudioMetadata, MetadataField
from .merger import MetadataMerger

__all__ = ['AudioMetadata', 'MetadataField', 'MetadataMerger']
