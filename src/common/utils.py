"""通用工具函数模块"""

import re
from urllib.parse import urlparse, parse_qs, urlunparse
from typing import Optional


class StringUtils:
    """字符串处理工具类"""
    
    @staticmethod
    def truncate(text: str, max_length: int = 30, suffix: str = '...') -> str:
        """截断过长的文本"""
        if len(text) <= max_length:
            return text
        return text[:max_length - len(suffix)] + suffix
    
    @staticmethod
    def clean_text(text: str) -> str:
        """清理文本中的多余空白"""
        if not text:
            return ''
        return ' '.join(text.split())
    
    @staticmethod
    def join_list(items: list, separator: str = '/') -> str:
        """将列表连接为字符串"""
        if not items:
            return ''
        return separator.join(str(item) for item in items if item)


class URLUtils:
    """URL 处理工具类"""
    
    @staticmethod
    def convert_to_song_url(url: str) -> str:
        """
        确保链接是单曲视图，以便获取详细 Credit
        
        Args:
            url: Apple Music URL
            
        Returns:
            转换后的单曲 URL
        """
        try:
            parsed = urlparse(url)
            query = parse_qs(parsed.query)
            if 'i' in query and '/album/' in parsed.path:
                song_id = query['i'][0]
                new_path = parsed.path.replace('/album/', '/song/')
                new_path = re.sub(r'/\d+$', f'/{song_id}', new_path)
                return urlunparse((parsed.scheme, parsed.netloc, new_path, '', '', ''))
        except Exception:
            pass
        return url
    
    @staticmethod
    def is_valid_url(url: str) -> bool:
        """检查 URL 是否有效"""
        try:
            result = urlparse(url)
            return all([result.scheme, result.netloc])
        except Exception:
            return False
